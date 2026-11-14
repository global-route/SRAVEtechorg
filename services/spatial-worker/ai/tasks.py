import json
import os
import structlog
from celery import Celery
import redis as sync_redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")
celery_app = Celery("spatial_worker", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_routes = {
    "ai_tasks.run_extraction": {"queue": "celery"},
}

log = structlog.get_logger()

JOB_TTL_COMPLETE = int(os.getenv("JOB_TTL_COMPLETE_SECONDS", 21600))
JOB_TTL_FAILED   = int(os.getenv("JOB_TTL_FAILED_SECONDS",   86400))


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


@celery_app.task(name="ai_tasks.run_extraction", bind=True, max_retries=1)
def run_extraction(self, job_id: str, lga_id: str, tif_path: str):
    try:
        _set_job(job_id, {"status": "extracting", "lga_id": lga_id})
        log.info("extraction_started", job_id=job_id, lga_id=lga_id)

        from ai.detector import detect_buildings
        buildings = detect_buildings(tif_path)

        from ingestion.postgis_writer import write_footprints
        count = write_footprints(lga_id, buildings)

        _set_job(job_id, {"status": "complete", "lga_id": lga_id, "buildings_detected": count},
                 ttl=JOB_TTL_COMPLETE)
        log.info("extraction_complete", job_id=job_id, lga_id=lga_id, buildings_detected=count)

    except Exception as exc:
        log.error("extraction_failed", job_id=job_id, lga_id=lga_id, error=str(exc),
                  retries=self.request.retries)
        _set_job(job_id, {"status": "failed", "error": str(exc)}, ttl=JOB_TTL_FAILED)
        if self.request.retries >= self.max_retries:
            _write_failed_job(
                "ai_tasks.run_extraction", job_id, lga_id, str(exc),
                {"tif_path": tif_path}, self.request.retries,
            )
        raise self.retry(exc=exc, countdown=30)
