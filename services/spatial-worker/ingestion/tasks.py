import os
import json
import structlog
from celery import Celery
import redis as sync_redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")
celery_app = Celery("spatial_worker", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_routes = {
    "ingest_worker.run":      {"queue": "celery"},
    "ingest_worker.dead":     {"queue": "dead_letter"},
}

log = structlog.get_logger()

JOB_TTL_COMPLETE = int(os.getenv("JOB_TTL_COMPLETE_SECONDS", 21600))   # 6 h
JOB_TTL_FAILED   = int(os.getenv("JOB_TTL_FAILED_SECONDS",   86400))   # 24 h


def _set_job(job_id: str, data: dict, ttl: int | None = None) -> None:
    r = sync_redis.from_url(REDIS_URL)
    r.setex(f"job:{job_id}", ttl or JOB_TTL_COMPLETE, json.dumps(data))
    r.close()


def _write_failed_job(task_name: str, job_id: str, lga_id: str, error: str, payload: dict, retries: int) -> None:
    import psycopg2, os as _os
    try:
        conn = psycopg2.connect(
            host=_os.getenv("DB_HOST", "postgres-db"),
            port=int(_os.getenv("DB_PORT", 5432)),
            dbname=_os.getenv("DB_NAME", "srave_prod"),
            user=_os.getenv("DB_USER", "srave_user"),
            password=_os.getenv("DB_PASSWORD"),
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO failed_jobs (task_name, job_id, lga_id, error, payload, retries) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (task_name, job_id, lga_id, error, json.dumps(payload), retries),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as db_err:
        log.error("failed_job_write_error", error=str(db_err))


@celery_app.task(name="ingest_worker.run", bind=True, max_retries=2)
def run_ingest(self, job_id: str, lga_id: str, bbox: list, source: str, resolution_m: float):
    try:
        _set_job(job_id, {"status": "processing", "lga_id": lga_id})
        log.info("ingest_started", job_id=job_id, lga_id=lga_id)

        from ingestion.gee_client import init_gee, fetch_imagery, export_geotiff
        init_gee()
        image = fetch_imagery(bbox)
        tif_path = export_geotiff(image, bbox, job_id, resolution_m)

        _set_job(job_id, {"status": "imagery_ready", "lga_id": lga_id, "tif_path": tif_path})
        log.info("imagery_ready", job_id=job_id, lga_id=lga_id)

        from ai.tasks import run_extraction
        run_extraction.delay(job_id, lga_id, tif_path)

    except Exception as exc:
        log.error("ingest_failed", job_id=job_id, lga_id=lga_id, error=str(exc),
                  retries=self.request.retries)
        _set_job(job_id, {"status": "failed", "error": str(exc)}, ttl=JOB_TTL_FAILED)
        if self.request.retries >= self.max_retries:
            _write_failed_job(
                "ingest_worker.run", job_id, lga_id, str(exc),
                {"bbox": bbox, "source": source, "resolution_m": resolution_m},
                self.request.retries,
            )
        raise self.retry(exc=exc, countdown=60)
