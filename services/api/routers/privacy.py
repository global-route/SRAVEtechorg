from fastapi import APIRouter, Depends
from repository.db import get_pool
from middleware.auth import require_scope

router = APIRouter()


@router.get("/dsar/{phone}")
async def get_dsar(phone: str, _=Depends(require_scope("admin"))):
    pool = await get_pool()
    roll = await pool.fetch("SELECT * FROM tax_roll WHERE owner_phone=$1", phone)
    assessments = await pool.fetch(
        "SELECT ta.* FROM tax_assessments ta "
        "JOIN tax_roll tr ON tr.id = ta.building_id WHERE tr.owner_phone=$1",
        phone,
    )
    return {"phone": phone, "tax_roll": [dict(r) for r in roll], "assessments": [dict(r) for r in assessments]}


@router.delete("/dsar/{phone}")
async def delete_dsar(phone: str, _=Depends(require_scope("admin"))):
    pool = await get_pool()
    await pool.execute(
        "UPDATE tax_roll SET owner_phone=NULL, owner_name=NULL WHERE owner_phone=$1", phone
    )
    return {"phone": phone, "status": "pii_removed"}
