import os
from fastapi import APIRouter, Depends, HTTPException
import httpx

from repository.db import get_pool
from middleware.auth import require_scope

router = APIRouter()
BILLING_URL = os.getenv("BILLING_SERVICE_URL", "http://billing-worker:8002")


@router.post("/assess/{building_id}", status_code=201)
async def assess_building(building_id: int, _=Depends(require_scope("municipal", "admin"))):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BILLING_URL}/assess/{building_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Building not found")
    return r.json()


@router.get("/assessment/{assessment_id}")
async def get_assessment(
    assessment_id: int,
    _=Depends(require_scope("municipal", "field_agent", "admin")),
):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM tax_assessments WHERE id=$1", assessment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return dict(row)


@router.get("/lga/{lga_id}/assessments")
async def lga_assessments(
    lga_id: str,
    page: int = 1,
    limit: int = 50,
    status: str | None = None,
    _=Depends(require_scope("municipal", "admin")),
):
    pool = await get_pool()
    offset = (page - 1) * limit
    rows = await pool.fetch(
        "SELECT ta.* FROM tax_assessments ta "
        "JOIN detected_buildings db ON db.id = ta.building_id "
        "WHERE db.lga_id=$1 LIMIT $2 OFFSET $3",
        lga_id, limit, offset,
    )
    return {"lga_id": lga_id, "assessments": [dict(r) for r in rows]}


@router.post("/voice-notice/{assessment_id}")
async def voice_notice(
    assessment_id: int,
    language: str = "yoruba",
    _=Depends(require_scope("municipal", "admin")),
):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{os.getenv('VOICE_SERVICE_URL', 'http://voice-service:8004')}/voice/notice/{assessment_id}",
            json={"language": language},
        )
    return r.json()
