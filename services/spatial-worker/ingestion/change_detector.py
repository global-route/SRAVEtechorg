import os
import asyncpg
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


async def detect_changes_v2(
    pool: asyncpg.Pool,
    lga_id: str,
    from_tif: str,
    to_tif: str,
    from_date: str,
    to_date: str,
    change_threshold: float = 0.20,
) -> dict:
    """
    Pixel-level temporal diff between two GeoTIFF scans.
    Detects: new structures, demolished structures, extensions (>20% area growth),
    partial demolitions (>20% area shrink).
    Writes results to change_detection_log.
    """
    with rasterio.open(from_tif) as src_from:
        arr_from = src_from.read([1, 2, 3]).astype(np.float32)
        transform = src_from.transform
        crs = src_from.crs

    with rasterio.open(to_tif) as src_to:
        arr_to = src_to.read([1, 2, 3]).astype(np.float32)

    # Normalise to [0,1]
    arr_from /= 255.0
    arr_to   /= 255.0

    # Per-pixel absolute difference (mean across RGB bands)
    diff = np.abs(arr_to - arr_from).mean(axis=0)

    # Threshold: pixels with >20% change are flagged
    changed_mask = (diff > change_threshold).astype(np.uint8)

    # Vectorise changed regions
    from rasterio.features import shapes as rasterio_shapes
    changed_polys = [
        shape(geom)
        for geom, val in rasterio_shapes(changed_mask, transform=transform)
        if val == 1
    ]

    if not changed_polys:
        return {
            "lga_id": lga_id,
            "period": {"from": from_date, "to": to_date},
            "new_structures": 0,
            "demolished_structures": 0,
            "modified_structures": 0,
            "pixel_diff_method": True,
        }

    changed_union = unary_union(changed_polys).simplify(0.000005)

    # Cross-reference with detected_buildings to classify change type
    rows_from = await pool.fetch(
        "SELECT id, footprint FROM detected_buildings WHERE lga_id=$1 AND scan_date=$2::date",
        lga_id, from_date,
    )
    rows_to = await pool.fetch(
        "SELECT id, footprint FROM detected_buildings WHERE lga_id=$1 AND scan_date=$2::date",
        lga_id, to_date,
    )

    from_geoms = {r["id"]: shape(r["footprint"]) for r in rows_from}
    to_geoms   = {r["id"]: shape(r["footprint"]) for r in rows_to}

    new_count = demolished_count = modified_count = 0
    logged = 0

    # New: in to_date, intersects changed region, no close match in from_date
    for bid, geom in to_geoms.items():
        if not geom.intersects(changed_union):
            continue
        has_match = any(
            geom.centroid.distance(fg.centroid) < 0.00002
            for fg in from_geoms.values()
        )
        if not has_match:
            new_count += 1
            await pool.execute(
                "INSERT INTO change_detection_log "
                "(building_id, change_type, from_scan_date, to_scan_date) "
                "VALUES ($1,'new',$2::date,$3::date) ON CONFLICT DO NOTHING",
                bid, from_date, to_date,
            )
            logged += 1

    # Demolished: in from_date, intersects changed region, no close match in to_date
    for bid, geom in from_geoms.items():
        if not geom.intersects(changed_union):
            continue
        has_match = any(
            geom.centroid.distance(tg.centroid) < 0.00002
            for tg in to_geoms.values()
        )
        if not has_match:
            demolished_count += 1
            await pool.execute(
                "INSERT INTO change_detection_log "
                "(building_id, change_type, from_scan_date, to_scan_date) "
                "VALUES ($1,'demolished',$2::date,$3::date) ON CONFLICT DO NOTHING",
                bid, from_date, to_date,
            )
            logged += 1

    # Modified: present in both, intersects changed region, area changed >20%
    for bid_f, geom_f in from_geoms.items():
        if not geom_f.intersects(changed_union):
            continue
        for bid_t, geom_t in to_geoms.items():
            if geom_f.centroid.distance(geom_t.centroid) < 0.00002:
                area_f = geom_f.area
                area_t = geom_t.area
                if area_f > 0:
                    ratio = abs(area_t - area_f) / area_f
                    if ratio > change_threshold:
                        change_type = "modified"
                        modified_count += 1
                        await pool.execute(
                            "INSERT INTO change_detection_log "
                            "(building_id, change_type, from_scan_date, to_scan_date) "
                            "VALUES ($1,$2,$3::date,$4::date) ON CONFLICT DO NOTHING",
                            bid_t, change_type, from_date, to_date,
                        )
                        logged += 1
                break

    return {
        "lga_id": lga_id,
        "period": {"from": from_date, "to": to_date},
        "new_structures": new_count,
        "demolished_structures": demolished_count,
        "modified_structures": modified_count,
        "flagged_for_field_review": new_count + modified_count,
        "pixel_diff_method": True,
        "change_log_entries": logged,
    }


# Legacy SQL-only change detection (kept for backward compatibility)
def detect_changes(lga_id: str, from_date: str, to_date: str) -> dict:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "pgbouncer"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT COUNT(*) AS cnt FROM detected_buildings new_b
        WHERE new_b.lga_id = %s AND new_b.scan_date = %s::date
          AND NOT EXISTS (
              SELECT 1 FROM detected_buildings old_b
              WHERE old_b.lga_id = %s AND old_b.scan_date = %s::date
                AND ST_DWithin(new_b.footprint::geography, old_b.footprint::geography, 5)
          )
    """, (lga_id, to_date, lga_id, from_date))
    new_count = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT COUNT(*) AS cnt FROM detected_buildings old_b
        WHERE old_b.lga_id = %s AND old_b.scan_date = %s::date
          AND NOT EXISTS (
              SELECT 1 FROM detected_buildings new_b
              WHERE new_b.lga_id = %s AND new_b.scan_date = %s::date
                AND ST_DWithin(old_b.footprint::geography, new_b.footprint::geography, 5)
          )
    """, (lga_id, from_date, lga_id, to_date))
    demolished_count = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM detected_buildings old_b
        JOIN detected_buildings new_b
          ON old_b.lga_id = new_b.lga_id
         AND ST_DWithin(old_b.footprint::geography, new_b.footprint::geography, 5)
        WHERE old_b.lga_id = %s
          AND old_b.scan_date = %s::date
          AND new_b.scan_date = %s::date
          AND (
              ST_Area(ST_Intersection(old_b.footprint, new_b.footprint)) /
              NULLIF(ST_Area(ST_Union(old_b.footprint, new_b.footprint)), 0)
          ) < 0.85
    """, (lga_id, from_date, to_date))
    modified_count = cur.fetchone()["cnt"]

    cur.execute("""
        INSERT INTO change_detection_log (building_id, change_type, from_scan_date, to_scan_date)
        SELECT new_b.id, 'new', %s::date, %s::date
        FROM detected_buildings new_b
        WHERE new_b.lga_id = %s AND new_b.scan_date = %s::date
          AND NOT EXISTS (
              SELECT 1 FROM detected_buildings old_b
              WHERE old_b.lga_id = %s AND old_b.scan_date = %s::date
                AND ST_DWithin(new_b.footprint::geography, old_b.footprint::geography, 5)
          )
        ON CONFLICT DO NOTHING
    """, (from_date, to_date, lga_id, to_date, lga_id, from_date))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "lga_id": lga_id,
        "period": {"from": from_date, "to": to_date},
        "new_structures": new_count,
        "modified_structures": modified_count,
        "demolished_structures": demolished_count,
        "flagged_for_field_review": new_count + modified_count,
        "pixel_diff_method": False,
    }
