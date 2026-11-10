import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("redis.asyncio.from_url") as mock_redis_factory:
        mock_r = AsyncMock()
        mock_r.setex = AsyncMock()
        mock_r.get = AsyncMock(return_value=None)
        mock_r.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_r

        from main import app
        yield TestClient(app), mock_r


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ingest_queued(client):
    c, mock_r = client
    with patch("ingestion.tasks.run_ingest") as mock_task:
        mock_task.delay = AsyncMock()
        r = c.post("/ingestion/ingest", json={
            "lga_id": "NGA025012",
            "bounding_box": [3.3792, 6.5244, 3.4000, 6.5500],
        })
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "queued"
    assert data["lga_id"] == "NGA025012"
    assert "job_id" in data


def test_ingest_invalid_bbox(client):
    c, _ = client
    r = c.post("/ingestion/ingest", json={
        "lga_id": "NGA025012",
        "bounding_box": [3.3792, 6.5244],  # only 2 values
    })
    assert r.status_code == 422


def test_ingest_bbox_out_of_nigeria(client):
    c, _ = client
    r = c.post("/ingestion/ingest", json={
        "lga_id": "NGA025012",
        "bounding_box": [-10.0, 6.5244, -9.0, 6.5500],  # outside Nigeria lon range
    })
    assert r.status_code == 422


def test_ingest_status_not_found(client):
    c, _ = client
    r = c.get("/ingestion/ingest/nonexistent-job-id")
    assert r.json()["status"] == "not_found"


def test_extract_job_not_found(client):
    c, _ = client
    r = c.post("/ai/extract/nonexistent-job-id")
    assert r.status_code == 404


def test_extract_job_not_ready(client):
    c, mock_r = client
    mock_r.get = AsyncMock(return_value=json.dumps({"status": "queued", "lga_id": "NGA025012"}).encode())
    r = c.post("/ai/extract/some-job-id")
    assert r.status_code == 409
