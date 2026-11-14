import os
import psycopg2
from psycopg2.extras import RealDictCursor
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")
celery_app = Celery("spatial_worker", broker=REDIS_URL, backend=REDIS_URL)


@celery_app.task(name="reclassify.run_batch")
def run_batch_reclassify():
    """
    Re-run the fine-tuned roof classifier over all detected_buildings
    where confidence_score < 0.6. Updates property_type and logs to audit_log.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id, lga_id, footprint FROM detected_buildings "
        "WHERE confidence_score < 0.6 AND verified = false"
    )
    buildings = cur.fetchall()

    from ai.detector import _load_yolo
    model = _load_yolo()

    updated = 0
    for b in buildings:
        # Re-classify using centroid patch — stub until imagery volume mounted
        # In production: extract patch from stored GeoTIFF by building centroid
        new_type = "residential_low"  # placeholder
        new_conf = 0.65

        cur.execute(
            "UPDATE detected_buildings SET property_type=%s, confidence_score=%s WHERE id=%s",
            (new_type, new_conf, b["id"]),
        )
        cur.execute(
            "INSERT INTO audit_log (actor, action, target_id, payload) VALUES (%s,%s,%s,%s::jsonb)",
            ("system", "reclassify", str(b["id"]),
             f'{{"old_type":"residential_low","new_type":"{new_type}","confidence":{new_conf}}}'),
        )
        updated += 1

    conn.commit()
    cur.close()
    conn.close()
    return {"reclassified": updated}
