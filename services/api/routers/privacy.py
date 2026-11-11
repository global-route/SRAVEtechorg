from fastapi import APIRouter, Depends, Request
from middleware.auth import require_scope

router = APIRouter()


@router.get("/dsar/{phone}")
async def get_dsar(phone: str, request: Request, _=Depends(require_scope("admin"))):
    pool = request.app.state.pool
    roll = await pool.fetch("SELECT id, lga_id, owner_language, registered_at FROM tax_roll WHERE owner_phone=$1", phone)
    assessments = await pool.fetch(
        "SELECT ta.id, ta.amount_due, ta.wa_status, ta.assessed_at FROM tax_assessments ta "
        "JOIN tax_roll tr ON tr.id = ta.building_id WHERE tr.owner_phone=$1", phone,
    )
    return {
        "phone": phone,
        "tax_roll": [dict(r) for r in roll],
        "assessments": [dict(r) for r in assessments],
        "exemptions": [
            {
                "table": "tax_assessments",
                "field": "owner_phone",
                "reason": "Financial record — exempt from erasure under NDPA Article 25. Assessment records are retained for statutory audit purposes.",
            }
        ],
    }


@router.delete("/dsar/{phone}")
async def delete_dsar(phone: str, request: Request, _=Depends(require_scope("admin"))):
    await request.app.state.pool.execute(
        "UPDATE tax_roll SET owner_phone=NULL, owner_name=NULL WHERE owner_phone=$1", phone
    )
    return {"phone": phone, "status": "pii_removed"}
