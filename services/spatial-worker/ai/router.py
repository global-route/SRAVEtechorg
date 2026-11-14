import json
import os
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-cache:6379")


@router.post("/extract/{job_id}", status_code=202)
async def extract_footprints(job_id: str):
    r = aioredis.from_url(REDIS_URL)
    raw = await r.get(f"job:{job_id}")
    await r.aclose()

    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")

    job = json.loads(raw)
    if job.get("status") != "imagery_ready":
        raise HTTPException(
            status_code=409,
            detail=f"Job not ready for extraction (status: {job.get('status')})",
        )

    from ai.tasks import run_extraction
    run_extraction.delay(job_id, job["lga_id"], job["tif_path"])

    return {"job_id": job_id, "status": "extracting", "models": ["YOLOv8m-seg", "SAM-ViT-H"]}


@router.get("/extract/{job_id}")
async def extraction_status(job_id: str):
    r = aioredis.from_url(REDIS_URL)
    raw = await r.get(f"job:{job_id}")
    await r.aclose()

    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job_id": job_id, **json.loads(raw)}
