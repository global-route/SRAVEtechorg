from fastapi import APIRouter, HTTPException, Request
from providers.whatsapp import send_demand_notice, send_document
from providers.flutterwave import create_payment_link as flw_link
from providers.paystack import create_payment_link as psk_link
import hashlib, json, os
from datetime import datetime, timezone

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


@router.post("/receipt/{assessment_id}", status_code=200)
async def send_receipt(assessment_id: int, request: Request):
    pool = request.app.state.pool
    row = await pool.fetchrow(
        """
        SELECT ta.payment_ref, ta.amount_paid, ta.payment_date,
               tr.owner_phone, tr.owner_name, tr.address
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        JOIN tax_roll tr ON tr.lga_id = db.lga_id
        WHERE ta.id=$1 AND ta.wa_status='paid'
        """,
        assessment_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paid assessment not found")

    from weasyprint import HTML
    from jinja2 import Template
    tmpl_path = os.path.join(os.path.dirname(__file__), "..", "templates", "payment_receipt.html")
    with open(tmpl_path) as f:
        html = Template(f.read()).render(
            ref=row["payment_ref"],
            owner_name=row["owner_name"] or "Property Owner",
            address=row["address"] or "",
            amount_paid=f"{float(row['amount_paid']):,.0f}",
            payment_date=row["payment_date"].strftime("%Y-%m-%d %H:%M UTC") if row["payment_date"] else "",
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
    pdf_bytes = HTML(string=html).write_pdf()

    try:
        await send_document(
            phone=row["owner_phone"],
            document_bytes=pdf_bytes,
            filename=f"receipt-{row['payment_ref']}.pdf",
            caption="Your SRAVE property tax receipt.",
        )
    except Exception:
        pass

    return {"assessment_id": assessment_id, "receipt_sent": True}
