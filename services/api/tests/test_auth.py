import pytest
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

SECRET = "test_secret"
ALGORITHM = "HS256"


def make_token(scope: str, expired: bool = False) -> str:
    exp = datetime.utcnow() + (timedelta(seconds=-1) if expired else timedelta(hours=1))
    return jwt.encode({"sub": "test", "scope": scope, "exp": exp}, SECRET, algorithm=ALGORITHM)


@pytest.fixture
def client():
    import os
    os.environ["JWT_SECRET"] = SECRET
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PASSWORD"] = "test"
    os.environ["REDIS_URL"] = "redis://localhost:6379"

    from main import app

    mock_pool = MagicMock()
    mock_pool.fetchval = AsyncMock(return_value=1)
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    app.state.pool = mock_pool
    app.state.redis = mock_redis

    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_protected_no_token(client):
    r = client.get("/api/v1/audit/lga/NGA025012/gap-analysis")
    assert r.status_code == 403


def test_protected_wrong_scope(client):
    token = make_token("field_agent")
    r = client.get(
        "/api/v1/audit/lga/NGA025012/gap-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_protected_expired_token(client):
    token = make_token("municipal", expired=True)
    r = client.get(
        "/api/v1/audit/lga/NGA025012/gap-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
