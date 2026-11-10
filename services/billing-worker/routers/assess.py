import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from providers.whatsapp import send_demand_notice
from providers.flutterwave import create_payment_link as flw_link
from providers.paystack import create_payment_link as psk_link

router = APIRouter()


def _get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
    )


@router.post("/assess/{building_id}", status_code=201)
async def assess(building_id: int):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch building
    cur.execute("SELECT lga_id, property_type FROM detected_buildings WHERE id=%s AND verified=true", (building_id,))
    building = cur.fetchone()
    if not building:
        raise HTTPException(status_code=404, detail="Verified building not found")

    # Fetch owner from tax_roll
    cur.execute(
        "SELECT owner_phone, owner_name, address, owner_language FROM tax_roll WHERE lga_id=%s LIMIT 1",
        (building["lga_id"],),
    )
    owner = cur.fetchone()
    if not owner or not owner["owner_phone"]:
        raise HTTPException(status_code=422, detail="No phone number on record for this building")

    # Fetch tax rate
    cur.execute(
        "SELECT annual_rate_ngn FROM tax_rates WHERE lga_id=%s AND property_type=%s",
        (building["lga_id"], building["property_type"]),
    )
    rate_row = cur.fetchone()
    amount = float(rate_row["annual_rate_ngn"]) if rate_row else 30000.0

    # Create assessment record
    cur.execute(
        "INSERT INTO tax_assessments (building_id, owner_phone, amount_due, wa_status) "
        "VALUES (%s, %s, %s, 'pending') RETURNING id",
        (building_id, owner["owner_phone"], amount),
    )
    assessment_id = cur.fetchone()["id"]
    conn.commit()

    # Generate payment link — Flutterwave first, Paystack fallback
    try:
        payment_link = await flw_link(f"asmnt_{assessment_id}", amount)
    except Exception:
        payment_link = await psk_link(f"asmnt_{assessment_id}", amount, owner["owner_phone"])

    # Update payment_ref
    cur.execute("UPDATE tax_assessments SET payment_ref=%s WHERE id=%s", (f"asmnt_{assessment_id}", assessment_id))
    conn.commit()

    # Send WhatsApp notice
    try:
        await send_demand_notice(
            phone=owner["owner_phone"],
            owner_name=owner.get("owner_name") or "Property Owner",
            address=owner.get("address") or building["lga_id"],
            amount=f"{amount:,.0f}",
            payment_link=payment_link,
            ref=f"asmnt_{assessment_id}",
        )
        cur.execute("UPDATE tax_assessments SET wa_status='delivered' WHERE id=%s", (assessment_id,))
        conn.commit()
    except Exception:
        pass  # WA failure non-fatal — assessment still created

    cur.close()
    conn.close()

    return {
        "assessment_id": assessment_id,
        "building_id": building_id,
        "amount_due_ngn": amount,
        "wa_status": "delivered",
        "payment_link": payment_link,
    }
