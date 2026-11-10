import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app

    mock_pool = MagicMock()
    app.state.pool = mock_pool
    return TestClient(app), mock_pool


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_assess_building_not_found(client):
    c, pool = client
    pool.fetchrow = AsyncMock(return_value=None)

    r = c.post("/assess/9999")
    assert r.status_code == 404


def test_assess_no_phone(client):
    c, pool = client
    pool.fetchrow = AsyncMock(side_effect=[
        {"lga_id": "NGA025012", "property_type": "residential_low"},
        {"owner_phone": None, "owner_name": None, "address": None, "owner_language": None},
    ])

    r = c.post("/assess/1")
    assert r.status_code == 422


def test_assess_success(client):
    c, pool = client
    pool.fetchrow = AsyncMock(side_effect=[
        {"lga_id": "NGA025012", "property_type": "residential_low"},
        {"owner_phone": "2348012345678", "owner_name": "Test Owner", "address": "12 Test St", "owner_language": "yoruba"},
        {"annual_rate_ngn": 30000.0},
    ])
    pool.fetchval = AsyncMock(return_value=42)
    pool.execute = AsyncMock()

    from unittest.mock import patch
    with patch("routers.assess.flw_link", new_callable=AsyncMock, return_value="https://pay.flw.co/test"), \
         patch("routers.assess.send_demand_notice", new_callable=AsyncMock):
        r = c.post("/assess/1")

    assert r.status_code == 201
    data = r.json()
    assert data["assessment_id"] == 42
    assert data["amount_due_ngn"] == 30000.0
    assert data["payment_link"] == "https://pay.flw.co/test"


def test_assess_paystack_fallback(client):
    c, pool = client
    pool.fetchrow = AsyncMock(side_effect=[
        {"lga_id": "NGA025012", "property_type": "commercial"},
        {"owner_phone": "2348099999999", "owner_name": "Biz Owner", "address": "5 Market Rd", "owner_language": "igbo"},
        {"annual_rate_ngn": 200000.0},
    ])
    pool.fetchval = AsyncMock(return_value=7)
    pool.execute = AsyncMock()

    from unittest.mock import patch
    with patch("routers.assess.flw_link", new_callable=AsyncMock, side_effect=Exception("flw down")), \
         patch("routers.assess.psk_link", new_callable=AsyncMock, return_value="https://paystack.co/test"), \
         patch("routers.assess.send_demand_notice", new_callable=AsyncMock):
        r = c.post("/assess/2")

    assert r.status_code == 201
    assert r.json()["payment_link"] == "https://paystack.co/test"
