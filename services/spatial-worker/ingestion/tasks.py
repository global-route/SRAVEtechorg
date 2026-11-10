import os
import json
from celery import Celery
import redis as sync_redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")
celery_app = Celery("spatial_worker", broker=REDIS_URL, backend=REDIS_URL)


def _set_job(job_id: str, data: dict) -> None:
    r = sync_redis.from_url(REDIS_URL)
    r.setex(f"job:{job_id}", 86400, json.dumps(data))
    r.close()


@celery_app.task(name="ingest_worker.run", bind=True, max_retries=2)
def run_ingest(self, job_id: str, lga_id: str, bbox: list, source: str, resolution_m: float):
    try:
        _set_job(job_id, {"status": "processing", "lga_id": lga_id})

        from ingestion.gee_client import init_gee, fetch_imagery, export_geotiff
        init_gee()
        image = fetch_imagery(bbox)
        tif_path = export_geotiff(image, bbox, job_id, resolution_m)

        _set_job(job_id, {"status": "imagery_ready", "lga_id": lga_id, "tif_path": tif_path})

        # Chain to AI extraction
        from ai.tasks import run_extraction
        run_extraction.delay(job_id, lga_id, tif_path)

    except Exception as exc:
        _set_job(job_id, {"status": "failed", "error": str(exc)})
        raise self.retry(exc=exc, countdown=60)
