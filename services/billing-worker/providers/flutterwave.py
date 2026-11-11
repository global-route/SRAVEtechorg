import os
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger()

FLW_URL = "https://api.flutterwave.com/v3/payments"
FLW_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
_DEGRADED_KEY = "circuit:flutterwave"
_DEGRADED_TTL = 60  # seconds


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
        log.warning("circuit_open", provider="flutterwave", ttl_seconds=_DEGRADED_TTL)
    except Exception:
        pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True,
)
async def _call_flutterwave(payload: dict) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            FLW_URL,
            json=payload,
            headers={"Authorization": f"Bearer {FLW_KEY}"},
        )
        r.raise_for_status()
        return r.json()["data"]["link"]


async def create_payment_link(assessment_id: str, amount_ngn: float) -> str:
    if _is_degraded():
        raise RuntimeError("Flutterwave circuit open — skipping to fallback")

    payload = {
        "tx_ref": assessment_id,
        "amount": amount_ngn,
        "currency": "NGN",
        "redirect_url": f"https://srave.io/payment/confirm/{assessment_id}",
        "meta": {"assessment_id": assessment_id},
    }
    try:
        return await _call_flutterwave(payload)
    except Exception as exc:
        _mark_degraded()
        log.error("flutterwave_failed", assessment_id=assessment_id, error=str(exc))
        raise
