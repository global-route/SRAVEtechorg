import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import redis.asyncio as aioredis
import json
import os

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")


class IngestRequest(BaseModel):
    lga_id: str
    bounding_box: List[float]
    source: str = "Sentinel-2"
    resolution_meters: float = 1.0


@router.post("/ingest", status_code=202)
async def trigger_ingest(payload: IngestRequest):
    job_id = str(uuid.uuid4())
    r = aioredis.from_url(REDIS_URL)
    await r.setex(
        f"job:{job_id}",
        86400,
        json.dumps({"status": "queued", "lga_id": payload.lga_id, "bbox": payload.bounding_box}),
    )
    await r.aclose()
    # TODO: dispatch Celery task: ingest_worker.run.delay(job_id, payload.dict())
    return {"job_id": job_id, "status": "queued", "lga_id": payload.lga_id}


@router.get("/ingest/{job_id}")
async def ingest_status(job_id: str):
    r = aioredis.from_url(REDIS_URL)
    raw = await r.get(f"job:{job_id}")
    await r.aclose()
    if not raw:
        return {"job_id": job_id, "status": "not_found"}
    return {"job_id": job_id, **json.loads(raw)}


@router.get("/changes/{lga_id}")
async def get_changes(lga_id: str, from_scan_date: str, to_scan_date: str):
    # TODO: run spatial diff between two scan dates via PostGIS IoU query
    return {
        "lga_id": lga_id,
        "period": {"from": from_scan_date, "to": to_scan_date},
        "new_structures": 0,
        "modified_structures": 0,
        "demolished_structures": 0,
        "flagged_for_field_review": 0,
    }
