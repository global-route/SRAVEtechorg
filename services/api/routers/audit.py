from fastapi import APIRouter, Depends, HTTPException
from repository.db import get_pool
from repository.gap import get_gap_analysis, get_daily_collections
from ledger.chain import append_snapshot, get_snapshots, verify_chain
from middleware.auth import require_scope

router = APIRouter()


@router.get("/lga/{lga_id}/gap-analysis")
async def gap_analysis(lga_id: str, _=Depends(require_scope("municipal", "admin"))):
    pool = await get_pool()
    result = await get_gap_analysis(pool, lga_id)
    if not result:
        raise HTTPException(status_code=404, detail="LGA not found")
    return result


@router.get("/lga/{lga_id}/buildings")
async def list_buildings(
    lga_id: str,
    page: int = 1,
    limit: int = 50,
    verified: bool | None = None,
    _=Depends(require_scope("municipal", "admin")),
):
    pool = await get_pool()
    offset = (page - 1) * limit
    filters = "AND verified = $3" if verified is not None else ""
    args = [lga_id, limit, offset] if verified is None else [lga_id, limit, offset, verified]
    rows = await pool.fetch(
        f"SELECT id, lga_id, confidence_score, property_type, verified, scan_date "
        f"FROM detected_buildings WHERE lga_id = $1 {filters} LIMIT $2 OFFSET $3",
        *args,
    )
    return {"lga_id": lga_id, "buildings": [dict(r) for r in rows]}


@router.get("/lga/{lga_id}/collections")
async def collections(lga_id: str, _=Depends(require_scope("municipal", "admin"))):
    pool = await get_pool()
    return await get_daily_collections(pool, lga_id)


@router.post("/snapshot", status_code=201)
async def create_snapshot(lga_id: str | None = None, _=Depends(require_scope("admin"))):
    pool = await get_pool()
    return await append_snapshot(pool, lga_id)


@router.get("/snapshots/{lga_id}")
async def list_snapshots(lga_id: str, _=Depends(require_scope("municipal", "admin"))):
    pool = await get_pool()
    return await get_snapshots(pool, lga_id)


@router.get("/snapshots/{lga_id}/verify-chain")
async def verify_chain_endpoint(lga_id: str, _=Depends(require_scope("municipal", "admin"))):
    pool = await get_pool()
    return await verify_chain(pool, lga_id)
