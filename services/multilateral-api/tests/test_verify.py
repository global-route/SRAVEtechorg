import pytest
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import os
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PASSWORD"] = "test"
    os.environ["PILOT_LGA"] = "Abeokuta South"

    from main import app

    mock_pool = MagicMock()
    mock_pool.fetchval = AsyncMock(return_value=1)
    mock_pool.fetchrow = AsyncMock(return_value={
        "total": 1000,
        "verified": 820,
        "collected_current": 41000000.0,
        "collected_prior": 30000000.0,
        "ledger_entry_hash": "sha256:abc123",
    })
    mock_pool.fetch = AsyncMock(return_value=[
        {
            "id": 1,
            "amount_due": 50000.0,
            "wa_status": "paid",
            "assessed_at": None,
            "lga_id": "Abeokuta South",
            "property_type": "residential_low",
        }
    ])
    app.state.pool = mock_pool
    return TestClient(app)


def test_verify_returns_200(client):
    r = client.get("/api/v1/multilateral/verify")
    assert r.status_code == 200
    data = r.json()
    assert "metrics" in data
    assert "signature_hash" in data
    assert data["signature_hash"].startswith("sha256:")
    assert "@context" in data


def test_verify_signature_matches_metrics(client):
    r = client.get("/api/v1/multilateral/verify")
    data = r.json()
    metrics = data["metrics"]
    canonical = json.dumps(metrics, sort_keys=True, default=str)
    expected = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    assert data["signature_hash"] == expected


def test_verify_has_chain_head(client):
    r = client.get("/api/v1/multilateral/verify")
    data = r.json()
    assert "chain_head_hash" in data


def test_ocds_export(client):
    r = client.get("/api/v1/multilateral/export/ocds?lga_id=Abeokuta+South")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    if items:
        assert "ocid" in items[0]
        assert items[0]["ocid"].startswith("ocds-srave-")


def test_public_key_endpoint(client):
    r = client.get("/.well-known/signing-key.pub")
    assert r.status_code == 200
