import os
import httpx

WA_TOKEN = os.getenv("WA_API_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
GRAPH_URL = "https://graph.facebook.com/v19.0"


async def upload_media(ogg_bytes: bytes) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GRAPH_URL}/{WA_PHONE_ID}/media",
            files={"file": ("notice.ogg", ogg_bytes, "audio/ogg; codecs=opus")},
            data={"messaging_product": "whatsapp"},
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
        )
        r.raise_for_status()
        return r.json()["id"]


async def send_voice_note(phone: str, media_id: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "audio",
        "audio": {"id": media_id, "voice": True},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GRAPH_URL}/{WA_PHONE_ID}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
        )
        r.raise_for_status()
