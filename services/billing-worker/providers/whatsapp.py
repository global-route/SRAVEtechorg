import os
import httpx

WA_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
WA_TOKEN = os.getenv("WA_API_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_NUMBER_ID", "")


async def send_demand_notice(
    phone: str, owner_name: str, address: str, amount: str, payment_link: str, ref: str
) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "tax_demand_notice",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": owner_name},
                        {"type": "text", "text": address},
                        {"type": "text", "text": amount},
                        {"type": "text", "text": payment_link},
                        {"type": "text", "text": ref},
                    ],
                }
            ],
        },
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            WA_URL.format(phone_number_id=WA_PHONE_ID),
            json=payload,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
        )
        r.raise_for_status()
