import hashlib
import json
from datetime import date, datetime
import asyncpg


async def _chain_head(pool: asyncpg.Pool, lga_id: str) -> str:
    row = await pool.fetchrow(
        "SELECT ledger_entry_hash FROM audit_snapshots WHERE lga_id=$1 ORDER BY snapshot_date DESC LIMIT 1",
        lga_id,
    )
    return row["ledger_entry_hash"] if row else "genesis"


def _compute_hash(previous_hash: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    raw = previous_hash + canonical
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


async def append_snapshot(pool: asyncpg.Pool, lga_id: str | None = None) -> list:
    if lga_id:
        lga_ids = [lga_id]
    else:
        rows = await pool.fetch("SELECT DISTINCT lga_id FROM detected_buildings")
        lga_ids = [r["lga_id"] for r in rows]

    results = []
    today = date.today()

    for lid in lga_ids:
        agg = await pool.fetchrow(
            """
            SELECT
                COUNT(db.id)                                                    AS total_buildings,
                COUNT(CASE WHEN db.verified THEN 1 END)                         AS verified_buildings,
                COUNT(ta.id)                                                    AS total_assessments,
                COALESCE(SUM(CASE WHEN ta.wa_status='paid' THEN ta.amount_due END), 0) AS total_collected_ngn
            FROM detected_buildings db
            LEFT JOIN tax_assessments ta ON ta.building_id = db.id
            WHERE db.lga_id = $1
            """,
            lid,
        )
        payload = {
            "lga_id": lid,
            "snapshot_date": str(today),
            "total_buildings": agg["total_buildings"],
            "verified_buildings": agg["verified_buildings"],
            "total_assessments": agg["total_assessments"],
            "total_collected_ngn": float(agg["total_collected_ngn"]),
        }
        prev_hash = await _chain_head(pool, lid)
        entry_hash = _compute_hash(prev_hash, payload)
        await pool.execute(
            "INSERT INTO audit_snapshots (lga_id, snapshot_date, ledger_entry_hash, previous_hash, payload_json) "
            "VALUES ($1,$2,$3,$4,$5)",
            lid, today, entry_hash, prev_hash, json.dumps(payload),
        )
        results.append({**payload, "ledger_entry_hash": entry_hash, "previous_hash": prev_hash, "immutable": True})
    return results


async def get_snapshots(pool: asyncpg.Pool, lga_id: str) -> list:
    rows = await pool.fetch(
        "SELECT * FROM audit_snapshots WHERE lga_id=$1 ORDER BY snapshot_date ASC", lga_id
    )
    return [dict(r) for r in rows]


async def verify_chain(pool: asyncpg.Pool, lga_id: str) -> dict:
    rows = await pool.fetch(
        "SELECT ledger_entry_hash, previous_hash, payload_json FROM audit_snapshots "
        "WHERE lga_id=$1 ORDER BY snapshot_date ASC",
        lga_id,
    )
    for row in rows:
        payload = json.loads(row["payload_json"])
        expected = _compute_hash(row["previous_hash"], payload)
        if expected != row["ledger_entry_hash"]:
            return {"chain_valid": False, "snapshots_checked": rows.index(row) + 1}
    return {"chain_valid": True, "snapshots_checked": len(rows)}
