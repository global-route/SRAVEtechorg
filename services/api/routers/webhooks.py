import hashlib
import hmac
import os
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(os.getenv("WA_APP_SECRET", "").encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")
    data = await request.json()
    pool = request.app.state.pool
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for status in change.get("value", {}).get("statuses", []):
                await pool.execute(
                    "UPDATE tax_assessments SET wa_status=$1 WHERE payment_ref=$2",
                    status["status"], status["id"],
                )
    return {"ok": True}


@router.post("/webhook/flutterwave")
async def flutterwave_webhook(request: Request):
    if request.headers.get("verif-hash") != os.getenv("FLUTTERWAVE_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid signature")
    data = await request.json()
    if data.get("event") == "charge.completed" and data["data"]["status"] == "successful":
        ref = data["data"]["tx_ref"]
        amount_paid = float(data["data"].get("amount", 0))
        row = await request.app.state.pool.fetchrow(
            "SELECT id, amount_due, amount_paid FROM tax_assessments WHERE payment_ref=$1", ref
        )
        if row:
            new_paid = float(row["amount_paid"]) + amount_paid
            new_status = "paid" if new_paid >= float(row["amount_due"]) else "partially_paid"
            await request.app.state.pool.execute(
                "UPDATE tax_assessments SET amount_paid=$1, wa_status=$2, payment_date=NOW() WHERE id=$3",
                new_paid, new_status, row["id"],
            )
    return {"ok": True}


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    body = await request.body()
    sig = hmac.new(os.getenv("PAYSTACK_SECRET_KEY", "").encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(request.headers.get("x-paystack-signature", ""), sig):
        raise HTTPException(status_code=403, detail="Invalid signature")
    data = await request.json()
    if data.get("event") == "charge.success":
        ref = data["data"]["reference"]
        amount_paid = float(data["data"].get("amount", 0)) / 100  # kobo → NGN
        row = await request.app.state.pool.fetchrow(
            "SELECT id, amount_due, amount_paid FROM tax_assessments WHERE payment_ref=$1", ref
        )
        if row:
            new_paid = float(row["amount_paid"]) + amount_paid
            new_status = "paid" if new_paid >= float(row["amount_due"]) else "partially_paid"
            await request.app.state.pool.execute(
                "UPDATE tax_assessments SET amount_paid=$1, wa_status=$2, payment_date=NOW() WHERE id=$3",
                new_paid, new_status, row["id"],
            )
    return {"ok": True}
