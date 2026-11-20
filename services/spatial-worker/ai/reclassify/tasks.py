import asyncio
import os
import asyncpg
from ingestion.tasks import celery_app


@celery_app.task(name="reclassify.run_batch")
def run_batch_reclassify():
    """
    Re-run the roof classifier over detected_buildings where confidence_score < 0.6.
    Updates property_type and logs to audit_log.
    Stub: real classification requires GeoTIFF patch extraction (phase 18-C).
    """
    return asyncio.get_event_loop().run_until_complete(_run())


async def _run() -> dict:
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "pgbouncer"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        rows = await conn.fetch(
            "SELECT id, lga_id FROM detected_buildings "
            "WHERE confidence_score < 0.6 AND verified = false"
        )
        updated = 0
        for row in rows:
            new_type = "residential_low"  # placeholder until 18-C
            new_conf = 0.65
            await conn.execute(
                "UPDATE detected_buildings SET property_type=$1, confidence_score=$2 WHERE id=$3",
                new_type, new_conf, row["id"],
            )
            await conn.execute(
                "INSERT INTO audit_log (actor, action, target_id, payload) "
                "VALUES ('system', 'reclassify', $1, $2::jsonb)",
                str(row["id"]),
                f'{{"new_type":"{new_type}","confidence":{new_conf}}}',
            )
            updated += 1
        return {"reclassified": updated}
    finally:
        await conn.close()
