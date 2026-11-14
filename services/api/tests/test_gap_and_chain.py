import pytest
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch


# --- Gap analysis tests ---

@pytest.mark.asyncio
async def test_gap_analysis_compliance_percentage():
    from services.api.repository.gap import get_gap_analysis

    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "total_detected": 100,
        "registered": 20,
        "gap": 80,
        "estimated_gap_ngn": 2400000,
    })

    result = await get_gap_analysis(mock_pool, "NGA025012")
    assert result["compliance_percentage"] == 20.0
    assert result["unregistered_gap"] == 80
    assert result["estimated_annual_revenue_gap_ngn"] == 2400000.0


@pytest.mark.asyncio
async def test_gap_analysis_zero_total():
    from services.api.repository.gap import get_gap_analysis

    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "total_detected": 0, "registered": 0, "gap": 0, "estimated_gap_ngn": 0,
    })
    result = await get_gap_analysis(mock_pool, "NGA000000")
    assert result["compliance_percentage"] == 0.0


# --- Audit chain tests ---

def _make_hash(prev: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256((prev + canonical).encode()).hexdigest()


@pytest.mark.asyncio
async def test_chain_verify_valid():
    from services.api.ledger.chain import verify_chain

    payload1 = {"lga_id": "NGA025012", "snapshot_date": "2026-01-01",
                "total_buildings": 100, "verified_buildings": 20,
                "total_assessments": 15, "total_collected_ngn": 750000.0}
    hash1 = _make_hash("genesis", payload1)

    payload2 = {**payload1, "snapshot_date": "2026-01-02", "total_buildings": 105}
    hash2 = _make_hash(hash1, payload2)

    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[
        {"ledger_entry_hash": hash1, "previous_hash": "genesis", "payload_json": json.dumps(payload1)},
        {"ledger_entry_hash": hash2, "previous_hash": hash1, "payload_json": json.dumps(payload2)},
    ])

    result = await verify_chain(mock_pool, "NGA025012")
    assert result["chain_valid"] is True
    assert result["snapshots_checked"] == 2


@pytest.mark.asyncio
async def test_chain_verify_tampered():
    from services.api.ledger.chain import verify_chain

    payload = {"lga_id": "NGA025012", "snapshot_date": "2026-01-01",
               "total_buildings": 100, "verified_buildings": 20,
               "total_assessments": 15, "total_collected_ngn": 750000.0}
    real_hash = _make_hash("genesis", payload)
    tampered_payload = {**payload, "total_collected_ngn": 9999999.0}

    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[
        {"ledger_entry_hash": real_hash, "previous_hash": "genesis",
         "payload_json": json.dumps(tampered_payload)},  # payload tampered
    ])

    result = await verify_chain(mock_pool, "NGA025012")
    assert result["chain_valid"] is False
