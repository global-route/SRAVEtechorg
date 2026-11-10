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
        await request.app.state.pool.execute(
            "UPDATE tax_assessments SET wa_status='paid' WHERE payment_ref=$1",
            data["data"]["tx_ref"],
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
        await request.app.state.pool.execute(
            "UPDATE tax_assessments SET wa_status='paid' WHERE payment_ref=$1",
            data["data"]["reference"],
        )
    return {"ok": True}
