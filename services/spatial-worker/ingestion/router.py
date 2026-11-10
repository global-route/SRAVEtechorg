import uuid
import json
import os
import redis.asyncio as aioredis
from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from typing import List

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")

NG_LON = (2.0, 15.0)
NG_LAT = (4.0, 14.0)


class IngestRequest(BaseModel):
    lga_id: str
    bounding_box: List[float]
    source: str = "Sentinel-2"
    resolution_meters: float = 1.0

    @field_validator("bounding_box")
    @classmethod
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError("bounding_box must have 4 values: [min_lon, min_lat, max_lon, max_lat]")
        min_lon, min_lat, max_lon, max_lat = v
        if not (NG_LON[0] <= min_lon <= NG_LON[1] and NG_LON[0] <= max_lon <= NG_LON[1]):
            raise ValueError("bounding_box longitude out of Nigeria range")
        if not (NG_LAT[0] <= min_lat <= NG_LAT[1] and NG_LAT[0] <= max_lat <= NG_LAT[1]):
            raise ValueError("bounding_box latitude out of Nigeria range")
        return v


@router.post("/ingest", status_code=202)
async def trigger_ingest(payload: IngestRequest):
    job_id = str(uuid.uuid4())
    r = aioredis.from_url(REDIS_URL)
    await r.setex(f"job:{job_id}", 86400, json.dumps({"status": "queued", "lga_id": payload.lga_id}))
    await r.aclose()

    from ingestion.tasks import run_ingest
    run_ingest.delay(job_id, payload.lga_id, payload.bounding_box, payload.source, payload.resolution_meters)

    return {"job_id": job_id, "status": "queued", "lga_id": payload.lga_id, "estimated_completion_minutes": 12}


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
    from ingestion.change_detector import detect_changes
    return detect_changes(lga_id, from_scan_date, to_scan_date)
