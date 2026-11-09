from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class IngestRequest(BaseModel):
    lga_id: str
    bounding_box: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    source: str = "Sentinel-2"
    resolution_meters: float = 1.0


@router.post("/ingest")
async def ingest(payload: IngestRequest):
    # TODO: connect to Google Earth Engine, pull imagery, write to PostGIS
    return {"job_id": "job_placeholder", "status": "queued", "lga_id": payload.lga_id}


@router.get("/ingest/{job_id}")
async def ingest_status(job_id: str):
    # TODO: poll async job status from Redis
    return {"job_id": job_id, "status": "pending", "buildings_detected": 0}
