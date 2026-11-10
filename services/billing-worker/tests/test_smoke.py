import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_assess_building_not_found(client):
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch("routers.assess._get_conn", return_value=mock_conn):
        r = client.post("/assess/9999")
    assert r.status_code == 404


def test_assess_no_phone(client):
    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = [
        {"lga_id": "NGA025012", "property_type": "residential_low"},  # building
        {"owner_phone": None, "owner_name": None, "address": None, "owner_language": None},  # owner
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch("routers.assess._get_conn", return_value=mock_conn):
        r = client.post("/assess/1")
    assert r.status_code == 422


def test_assess_success(client):
    mock_cur = MagicMock()
    mock_cur.fetchone.side_effect = [
        {"lga_id": "NGA025012", "property_type": "residential_low"},
        {"owner_phone": "2348012345678", "owner_name": "Test Owner", "address": "12 Test St", "owner_language": "yoruba"},
        {"annual_rate_ngn": 30000.0},
        {"id": 42},
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch("routers.assess._get_conn", return_value=mock_conn), \
         patch("routers.assess.flw_link", new_callable=AsyncMock, return_value="https://pay.flw.co/test"), \
         patch("routers.assess.send_demand_notice", new_callable=AsyncMock):
        r = client.post("/assess/1")

    assert r.status_code == 201
    data = r.json()
    assert data["assessment_id"] == 42
    assert data["amount_due_ngn"] == 30000.0
    assert "payment_link" in data
