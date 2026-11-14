import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from jose import jwt

SECRET = "test_secret"


def make_token(scope: str) -> str:
    return jwt.encode(
        {"sub": "test", "scope": scope, "exp": datetime.utcnow() + timedelta(hours=1)},
        SECRET, algorithm="HS256",
    )


@pytest.fixture
def client():
    import os
    os.environ["JWT_SECRET"] = SECRET
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PASSWORD"] = "test"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["FLUTTERWAVE_SECRET_KEY"] = "test_flw_key"
    os.environ["PAYSTACK_SECRET_KEY"] = "test_psk_key"
    os.environ["WA_APP_SECRET"] = "test_wa_secret"

    from main import app
    mock_pool = MagicMock()
    mock_pool.fetchval = AsyncMock(return_value=1)
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.pipeline = MagicMock(return_value=MagicMock(
        zremrangebyscore=MagicMock(), zadd=MagicMock(), zcard=MagicMock(),
        expire=MagicMock(), execute=AsyncMock(return_value=[0, 0, 1, True])
    ))
    app.state.pool = mock_pool
    app.state.redis = mock_redis
    return TestClient(app)


def test_assess_requires_auth(client):
    r = client.post("/api/v1/billing/assess/1")
    assert r.status_code in (401, 403)


def test_flutterwave_webhook_invalid_sig(client):
    r = client.post(
        "/api/v1/billing/webhook/flutterwave",
        json={"event": "charge.completed", "data": {"status": "successful", "tx_ref": "asmnt_1"}},
        headers={"verif-hash": "wrong_key"},
    )
    assert r.status_code == 403


def test_paystack_webhook_invalid_sig(client):
    body = json.dumps({"event": "charge.success", "data": {"reference": "asmnt_1"}}).encode()
    bad_sig = "badhash"
    r = client.post(
        "/api/v1/billing/webhook/paystack",
        content=body,
        headers={"x-paystack-signature": bad_sig, "content-type": "application/json"},
    )
    assert r.status_code == 403


def test_paystack_webhook_valid_sig(client):
    import os
    body = json.dumps({"event": "charge.success", "data": {"reference": "asmnt_1"}}).encode()
    sig = hmac.new(os.environ["PAYSTACK_SECRET_KEY"].encode(), body, hashlib.sha512).hexdigest()

    mock_pool = client.app.state.pool
    mock_pool.execute = AsyncMock(return_value=None)

    r = client.post(
        "/api/v1/billing/webhook/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 200
