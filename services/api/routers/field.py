from fastapi import APIRouter, Depends
from models.schemas import VerifyPayload
from repository.db import get_pool
from middleware.auth import require_scope

router = APIRouter()


@router.get("/assignments/{agent_id}")
async def get_assignments(agent_id: str, _=Depends(require_scope("field_agent", "admin"))):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, lga_id, property_type, verified FROM detected_buildings "
        "WHERE verified = false ORDER BY created_at DESC LIMIT 50"
    )
    return {"agent_id": agent_id, "assignments": [dict(r) for r in rows]}


@router.patch("/buildings/{building_id}/verify", status_code=200)
async def verify_building(
    building_id: int,
    body: VerifyPayload,
    _=Depends(require_scope("field_agent", "admin")),
):
    pool = await get_pool()
    await pool.execute(
        "UPDATE detected_buildings SET verified=$1, property_type=COALESCE($2, property_type) WHERE id=$3",
        body.verified, body.property_type, building_id,
    )
    if body.owner_phone:
        await pool.execute(
            "INSERT INTO tax_roll (lga_id, owner_phone, owner_language) "
            "SELECT lga_id, $1, $2 FROM detected_buildings WHERE id=$3 "
            "ON CONFLICT DO NOTHING",
            body.owner_phone, body.owner_language, building_id,
        )
    return {"building_id": building_id, "verified": body.verified}
