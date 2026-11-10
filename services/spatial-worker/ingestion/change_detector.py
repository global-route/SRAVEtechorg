import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )


def detect_changes(lga_id: str, from_date: str, to_date: str) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # New structures: in to_date scan, no match within 5m in from_date scan
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

    # Demolished: in from_date, no match in to_date
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

    # Modified: present in both but IoU < 0.85
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

    # Write new structures to change_detection_log
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

    flagged = new_count + modified_count
    return {
        "lga_id": lga_id,
        "period": {"from": from_date, "to": to_date},
        "new_structures": new_count,
        "modified_structures": modified_count,
        "demolished_structures": demolished_count,
        "flagged_for_field_review": flagged,
    }
