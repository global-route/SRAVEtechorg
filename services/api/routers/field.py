import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from middleware.auth import require_scope

router = APIRouter()

PHOTO_DIR = os.getenv("PHOTO_STORAGE_PATH", "/data/photos")


@router.get("/assignments/{agent_id}")
async def get_assignments(agent_id: str, request: Request, _=Depends(require_scope("field_agent", "admin"))):
    rows = await request.app.state.pool.fetch(
        """
        SELECT db.id, db.lga_id, db.property_type, db.verified,
               cdl.change_type
        FROM detected_buildings db
        LEFT JOIN change_detection_log cdl ON cdl.building_id = db.id
        WHERE db.verified = false
        ORDER BY cdl.change_type NULLS LAST, db.created_at DESC
        LIMIT 50
        """
    )
    return {"agent_id": agent_id, "assignments": [dict(r) for r in rows]}


@router.patch("/buildings/{building_id}/verify")
async def verify_building(
    building_id: int,
    request: Request,
    _=Depends(require_scope("field_agent", "admin")),
):
    from models.schemas import VerifyPayload
    body = await request.json()
    payload = VerifyPayload(**body)
    pool = request.app.state.pool

    await pool.execute(
        "UPDATE detected_buildings SET verified=$1, property_type=COALESCE($2, property_type) WHERE id=$3",
        payload.verified, payload.property_type, building_id,
    )
    if payload.owner_phone:
        await pool.execute(
            "INSERT INTO tax_roll (lga_id, owner_phone, owner_language) "
            "SELECT lga_id, $1, $2 FROM detected_buildings WHERE id=$3 ON CONFLICT DO NOTHING",
            payload.owner_phone, payload.owner_language, building_id,
        )
    await pool.execute(
        "INSERT INTO audit_log (actor, action, target_id, payload) VALUES ($1,$2,$3,$4::jsonb)",
        "field_agent", "verify_building", str(building_id),
        f'{{"building_id":{building_id},"property_type":"{payload.property_type}"}}',
    )
    return {"building_id": building_id, "verified": payload.verified}


@router.post("/photos", status_code=201)
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    _=Depends(require_scope("field_agent", "admin")),
):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(PHOTO_DIR, filename)
    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)
    base_url = os.getenv("API_BASE_URL", "https://api.srave.io")
    return {"photo_url": f"{base_url}/photos/{filename}"}
