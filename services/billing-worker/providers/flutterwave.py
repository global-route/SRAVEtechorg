import os
import httpx

FLW_URL = "https://api.flutterwave.com/v3/payments"
FLW_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY", "")


async def create_payment_link(assessment_id: str, amount_ngn: float) -> str:
    payload = {
        "tx_ref": assessment_id,
        "amount": amount_ngn,
        "currency": "NGN",
        "redirect_url": f"https://srave.io/payment/confirm/{assessment_id}",
        "meta": {"assessment_id": assessment_id},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            FLW_URL,
            json=payload,
            headers={"Authorization": f"Bearer {FLW_KEY}"},
        )
        r.raise_for_status()
        return r.json()["data"]["link"]
