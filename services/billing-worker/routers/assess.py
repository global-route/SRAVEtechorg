from fastapi import APIRouter, HTTPException, Request
from providers.whatsapp import send_demand_notice
from providers.flutterwave import create_payment_link as flw_link
from providers.paystack import create_payment_link as psk_link

router = APIRouter()


@router.post("/assess/{building_id}", status_code=201)
async def assess(building_id: int, request: Request):
    pool = request.app.state.pool

    building = await pool.fetchrow(
        "SELECT lga_id, property_type FROM detected_buildings WHERE id=$1 AND verified=true",
        building_id,
    )
    if not building:
        raise HTTPException(status_code=404, detail="Verified building not found")

    owner = await pool.fetchrow(
        "SELECT owner_phone, owner_name, address, owner_language FROM tax_roll WHERE lga_id=$1 LIMIT 1",
        building["lga_id"],
    )
    if not owner or not owner["owner_phone"]:
        raise HTTPException(status_code=422, detail="No phone number on record for this building")

    rate_row = await pool.fetchrow(
        "SELECT annual_rate_ngn FROM tax_rates WHERE lga_id=$1 AND property_type=$2",
        building["lga_id"], building["property_type"],
    )
    amount = float(rate_row["annual_rate_ngn"]) if rate_row else 30000.0

    assessment_id = await pool.fetchval(
        "INSERT INTO tax_assessments (building_id, owner_phone, amount_due, wa_status) "
        "VALUES ($1,$2,$3,'pending') RETURNING id",
        building_id, owner["owner_phone"], amount,
    )

    ref = f"asmnt_{assessment_id}"
    try:
        payment_link = await flw_link(ref, amount)
    except Exception:
        payment_link = await psk_link(ref, amount, owner["owner_phone"])

    await pool.execute(
        "UPDATE tax_assessments SET payment_ref=$1 WHERE id=$2", ref, assessment_id
    )

    try:
        await send_demand_notice(
            phone=owner["owner_phone"],
            owner_name=owner["owner_name"] or "Property Owner",
            address=owner["address"] or building["lga_id"],
            amount=f"{amount:,.0f}",
            payment_link=payment_link,
            ref=ref,
        )
        await pool.execute(
            "UPDATE tax_assessments SET wa_status='delivered' WHERE id=$1", assessment_id
        )
    except Exception:
        pass  # WA failure non-fatal

    return {
        "assessment_id": assessment_id,
        "building_id": building_id,
        "amount_due_ngn": amount,
        "wa_status": "delivered",
        "payment_link": payment_link,
    }
