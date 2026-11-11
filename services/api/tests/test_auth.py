import pytest
import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

SECRET = "test_secret"
ALGORITHM = "HS256"


def make_token(scope: str, lga_id: str | None = None, expired: bool = False) -> str:
    exp = datetime.utcnow() + (timedelta(seconds=-1) if expired else timedelta(hours=1))
    return jwt.encode({"sub": "test", "scope": scope, "lga_id": lga_id, "exp": exp}, SECRET, algorithm=ALGORITHM)


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
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock()
    app.state.pool = mock_pool
    app.state.redis = mock_redis

    return TestClient(app), mock_pool, mock_redis


def test_health(client):
    c, _, __ = client
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_issue_token_success(client):
    c, pool, redis = client
    secret_hash = bcrypt.hashpw(b"test_secret", bcrypt.gensalt()).decode()
    pool.fetchrow = AsyncMock(return_value={
        "secret_hash": secret_hash,
        "scope": "municipal",
        "lga_id": "NGA025012",
    })
    r = c.post("/api/v1/auth/token", json={"client_id": "muni_01", "client_secret": "test_secret"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


def test_issue_token_wrong_secret(client):
    c, pool, _ = client
    secret_hash = bcrypt.hashpw(b"correct_secret", bcrypt.gensalt()).decode()
    pool.fetchrow = AsyncMock(return_value={
        "secret_hash": secret_hash,
        "scope": "municipal",
        "lga_id": "NGA025012",
    })
    r = c.post("/api/v1/auth/token", json={"client_id": "muni_01", "client_secret": "wrong_secret"})
    assert r.status_code == 401


def test_issue_token_unknown_client(client):
    c, pool, _ = client
    pool.fetchrow = AsyncMock(return_value=None)
    r = c.post("/api/v1/auth/token", json={"client_id": "unknown", "client_secret": "x"})
    assert r.status_code == 401


def test_refresh_token_success(client):
    c, pool, redis = client
    redis.get = AsyncMock(return_value=b"muni_01:municipal:NGA025012")
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": "valid_refresh_token"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    redis.delete.assert_called_once()


def test_refresh_token_invalid(client):
    c, _, redis = client
    redis.get = AsyncMock(return_value=None)
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": "bad_token"})
    assert r.status_code == 401


def test_protected_no_token(client):
    c, _, __ = client
    r = c.get("/api/v1/audit/lga/NGA025012/gap-analysis")
    assert r.status_code == 403


def test_protected_wrong_scope(client):
    c, _, __ = client
    token = make_token("field_agent", "NGA025012")
    r = c.get("/api/v1/audit/lga/NGA025012/gap-analysis",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_protected_expired_token(client):
    c, _, __ = client
    token = make_token("municipal", "NGA025012", expired=True)
    r = c.get("/api/v1/audit/lga/NGA025012/gap-analysis",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_lga_scope_isolation(client):
    c, pool, _ = client
    # Token for NGA025012 trying to access NGA999999
    token = make_token("municipal", "NGA025012")
    pool.fetchrow = AsyncMock(return_value=None)
    r = c.get("/api/v1/audit/lga/NGA999999/gap-analysis",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_bypasses_lga_isolation(client):
    c, pool, _ = client
    token = make_token("admin", None)
    pool.fetchrow = AsyncMock(return_value={
        "total_detected": 100, "registered": 80, "gap": 20, "estimated_gap_ngn": 600000
    })
    # Admin can access any LGA — should not get 403
    r = c.get("/api/v1/audit/lga/NGA999999/gap-analysis",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 403
