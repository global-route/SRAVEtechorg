import os
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger()

WA_URL     = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
WA_TOKEN   = os.getenv("WA_API_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
_DEGRADED_KEY = "circuit:whatsapp"
_DEGRADED_TTL = 60


def _is_degraded() -> bool:
    try:
        import redis as sync_redis
        r = sync_redis.from_url(os.getenv("REDIS_URL", "redis://redis-cache:6379"))
        result = r.exists(_DEGRADED_KEY)
        r.close()
        return bool(result)
    except Exception:
        return False


def _mark_degraded() -> None:
    try:
        import redis as sync_redis
        r = sync_redis.from_url(os.getenv("REDIS_URL", "redis://redis-cache:6379"))
        r.setex(_DEGRADED_KEY, _DEGRADED_TTL, "1")
        r.close()
        log.warning("circuit_open", provider="whatsapp", ttl_seconds=_DEGRADED_TTL)
    except Exception:
        pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True,
)
async def _send(payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            WA_URL.format(phone_number_id=WA_PHONE_ID),
            json=payload,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
        )
        r.raise_for_status()


async def send_demand_notice(
    phone: str, owner_name: str, address: str, amount: str, payment_link: str, ref: str
) -> None:
    if _is_degraded():
        raise RuntimeError("WhatsApp circuit open")

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "tax_demand_notice",
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": owner_name},
                    {"type": "text", "text": address},
                    {"type": "text", "text": amount},
                    {"type": "text", "text": payment_link},
                    {"type": "text", "text": ref},
                ],
            }],
        },
    }
    try:
        await _send(payload)
    except Exception as exc:
        _mark_degraded()
        log.error("whatsapp_failed", phone=phone, ref=ref, error=str(exc))
        raise
