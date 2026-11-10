import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app

    mock_pool = MagicMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "total": 1000,
        "verified": 850,
        "collected_current": 25500000.0,
        "collected_prior": 20000000.0,
        "ledger_entry_hash": "sha256:abc123",
    })
    mock_pool.fetch = AsyncMock(return_value=[])
    app.state.pool = mock_pool

    return TestClient(app), mock_pool


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_returns_signed_payload(client):
    c, mock_pool = client

    # fetchrow called twice: metrics query + chain head query
    mock_pool.fetchrow = AsyncMock(side_effect=[
        {
            "total": 1000, "verified": 850,
            "collected_current": 25500000.0, "collected_prior": 20000000.0,
        },
        {"ledger_entry_hash": "sha256:abc123"},
    ])

    r = c.get("/api/v1/multilateral/verify")
    assert r.status_code == 200
    data = r.json()
    assert "signature_hash" in data
    assert data["signature_hash"].startswith("sha256:")
    assert "metrics" in data
    assert "property_formalization_index" in data["metrics"]
    assert "issuing_authority" in data


def test_verify_with_lga_filter(client):
    c, mock_pool = client
    mock_pool.fetchrow = AsyncMock(side_effect=[
        {"total": 500, "verified": 400, "collected_current": 10000000.0, "collected_prior": 8000000.0},
        {"ledger_entry_hash": "sha256:def456"},
    ])
    r = c.get("/api/v1/multilateral/verify?lga_id=NGA025012")
    assert r.status_code == 200
    assert r.json()["verified_subnational_entity"] == "NGA025012"


def test_ocds_export(client):
    c, mock_pool = client
    mock_pool.fetch = AsyncMock(return_value=[])
    r = c.get("/api/v1/multilateral/export/ocds?lga_id=NGA025012")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_public_key_endpoint(client):
    c, _ = client
    with patch("routers.verify.get_public_key_pem", return_value="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----\n"):
        r = c.get("/.well-known/signing-key.pub")
    assert r.status_code == 200
    assert "public_key" in r.json()
