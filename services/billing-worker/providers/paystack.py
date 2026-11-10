import os
import httpx

PSK_URL = "https://api.paystack.co/transaction/initialize"
PSK_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")


async def create_payment_link(assessment_id: str, amount_ngn: float, phone: str = "") -> str:
    payload = {
        "reference": assessment_id,
        "amount": int(amount_ngn * 100),  # Paystack uses kobo
        "currency": "NGN",
        "metadata": {"assessment_id": assessment_id, "phone": phone},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            PSK_URL,
            json=payload,
            headers={"Authorization": f"Bearer {PSK_KEY}"},
        )
        r.raise_for_status()
        return r.json()["data"]["authorization_url"]
