import os
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger()

PSK_URL = "https://api.paystack.co/transaction/initialize"
PSK_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
_DEGRADED_KEY = "circuit:paystack"
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
        log.warning("circuit_open", provider="paystack", ttl_seconds=_DEGRADED_TTL)
    except Exception:
        pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True,
)
async def _call_paystack(payload: dict) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            PSK_URL,
            json=payload,
            headers={"Authorization": f"Bearer {PSK_KEY}"},
        )
        r.raise_for_status()
        return r.json()["data"]["authorization_url"]


async def create_payment_link(assessment_id: str, amount_ngn: float, phone: str = "") -> str:
    if _is_degraded():
        raise RuntimeError("Paystack circuit open")

    payload = {
        "reference": assessment_id,
        "amount": int(amount_ngn * 100),
        "currency": "NGN",
        "metadata": {"assessment_id": assessment_id, "phone": phone},
    }
    try:
        return await _call_paystack(payload)
    except Exception as exc:
        _mark_degraded()
        log.error("paystack_failed", assessment_id=assessment_id, error=str(exc))
        raise
