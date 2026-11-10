import os
from fastapi import APIRouter, Depends
import httpx

from middleware.auth import require_scope

router = APIRouter()
SPATIAL_URL = os.getenv("SPATIAL_SERVICE_URL", "http://spatial-worker:8001")


@router.post("/ingest", status_code=202)
async def trigger_ingest(payload: dict, _=Depends(require_scope("municipal", "admin"))):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SPATIAL_URL}/ingestion/ingest", json=payload)
    return r.json()


@router.get("/ingest/{job_id}")
async def ingest_status(job_id: str, _=Depends(require_scope("municipal", "admin"))):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SPATIAL_URL}/ingestion/ingest/{job_id}")
    return r.json()


@router.get("/lga/{lga_id}/changes")
async def get_changes(
    lga_id: str,
    from_scan_date: str,
    to_scan_date: str,
    _=Depends(require_scope("municipal", "admin")),
):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SPATIAL_URL}/ingestion/changes/{lga_id}",
            params={"from_scan_date": from_scan_date, "to_scan_date": to_scan_date},
        )
    return r.json()
