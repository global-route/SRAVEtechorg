import json
import os
import psycopg2
from psycopg2.extras import execute_values


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )


def write_footprints(lga_id: str, buildings: list[dict]) -> int:
    """
    Batch insert building footprints into detected_buildings.
    Skips duplicates within 2m of an existing footprint for the same scan_date.
    Returns count of inserted rows.
    """
    if not buildings:
        return 0

    conn = get_conn()
    cur = conn.cursor()

    rows = [
        (
            lga_id,
            json.dumps(b["footprint_geojson"]),
            b["confidence"],
            b["property_type"],
            b.get("scan_date"),
        )
        for b in buildings
    ]

    execute_values(
        cur,
        """
        INSERT INTO detected_buildings (lga_id, footprint, confidence_score, property_type, scan_date)
        SELECT
            v.lga_id,
            ST_GeomFromGeoJSON(v.footprint),
            v.confidence,
            v.property_type,
            v.scan_date::date
        FROM (VALUES %s) AS v(lga_id, footprint, confidence, property_type, scan_date)
        WHERE NOT EXISTS (
            SELECT 1 FROM detected_buildings db
            WHERE db.lga_id = v.lga_id
              AND db.scan_date = v.scan_date::date
              AND ST_DWithin(
                    db.footprint::geography,
                    ST_Centroid(ST_GeomFromGeoJSON(v.footprint))::geography,
                    2
                  )
        )
        """,
        rows,
        page_size=500,
    )

    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return count
