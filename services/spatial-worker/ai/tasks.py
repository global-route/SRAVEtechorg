import json
import os
import redis as sync_redis
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")
celery_app = Celery("spatial_worker", broker=REDIS_URL, backend=REDIS_URL)


def _set_job(job_id: str, data: dict) -> None:
    r = sync_redis.from_url(REDIS_URL)
    r.setex(f"job:{job_id}", 86400, json.dumps(data))
    r.close()


@celery_app.task(name="ai_tasks.run_extraction", bind=True, max_retries=1)
def run_extraction(self, job_id: str, lga_id: str, tif_path: str):
    try:
        _set_job(job_id, {"status": "extracting", "lga_id": lga_id})

        from ai.detector import detect_buildings
        buildings = detect_buildings(tif_path)

        from ingestion.postgis_writer import write_footprints
        count = write_footprints(lga_id, buildings)

        _set_job(job_id, {"status": "complete", "lga_id": lga_id, "buildings_detected": count})

    except Exception as exc:
        _set_job(job_id, {"status": "failed", "error": str(exc)})
        raise self.retry(exc=exc, countdown=30)
