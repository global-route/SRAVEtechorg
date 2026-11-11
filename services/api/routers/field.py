from fastapi import APIRouter, Depends, Request
from models.schemas import VerifyPayload
from middleware.auth import require_scope

router = APIRouter()


@router.get("/assignments/{agent_id}")
async def get_assignments(
    agent_id: str,
    request: Request,
    lga_id: str | None = None,
    page: int = 1,
    limit: int = 50,
    _=Depends(require_scope("field_agent", "admin")),
):
    offset = (page - 1) * limit
    if lga_id:
        rows = await request.app.state.pool.fetch(
            "SELECT id, lga_id, property_type, verified, confidence_score FROM detected_buildings "
            "WHERE verified=false AND lga_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            lga_id, limit, offset,
        )
    else:
        rows = await request.app.state.pool.fetch(
            "SELECT id, lga_id, property_type, verified, confidence_score FROM detected_buildings "
            "WHERE verified=false ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
    return {"agent_id": agent_id, "lga_id": lga_id, "page": page, "assignments": [dict(r) for r in rows]}


@router.patch("/buildings/{building_id}/verify")
async def verify_building(
    building_id: int,
    body: VerifyPayload,
    request: Request,
    _=Depends(require_scope("field_agent", "admin")),
):
    pool = request.app.state.pool
    await pool.execute(
        "UPDATE detected_buildings "
        "SET verified=$1, property_type=COALESCE($2, property_type), photo_url=COALESCE($3, photo_url) "
        "WHERE id=$4",
        body.verified, body.property_type, body.photo_url, building_id,
    )
    if body.owner_phone:
        await pool.execute(
            "INSERT INTO tax_roll (lga_id, owner_phone, owner_language) "
            "SELECT lga_id, $1, $2 FROM detected_buildings WHERE id=$3 ON CONFLICT DO NOTHING",
            body.owner_phone, body.owner_language, building_id,
        )
    return {"building_id": building_id, "verified": body.verified}
