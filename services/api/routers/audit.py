from fastapi import APIRouter, Depends, HTTPException, Request
from repository.gap import get_gap_analysis, get_daily_collections
from ledger.chain import append_snapshot, get_snapshots, verify_chain
from middleware.auth import require_scope, require_scope_and_lga

router = APIRouter()


@router.get("/lga/{lga_id}/gap-analysis")
async def gap_analysis(lga_id: str, request: Request, _=Depends(require_scope_and_lga("municipal", "admin"))):
    result = await get_gap_analysis(request.app.state.pool, lga_id)
    if not result:
        raise HTTPException(status_code=404, detail="LGA not found")
    return result


@router.get("/lga/{lga_id}/buildings")
async def list_buildings(
    lga_id: str,
    request: Request,
    page: int = 1,
    limit: int = 50,
    verified: bool | None = None,
    _=Depends(require_scope_and_lga("municipal", "admin")),
):
    offset = (page - 1) * limit
    q = "SELECT id, lga_id, confidence_score, property_type, verified, scan_date FROM detected_buildings WHERE lga_id=$1"
    args = [lga_id]
    if verified is not None:
        q += " AND verified=$2 LIMIT $3 OFFSET $4"
        args += [verified, limit, offset]
    else:
        q += " LIMIT $2 OFFSET $3"
        args += [limit, offset]
    rows = await request.app.state.pool.fetch(q, *args)
    return {"lga_id": lga_id, "buildings": [dict(r) for r in rows]}


@router.get("/lga/{lga_id}/collections")
async def collections(lga_id: str, request: Request, _=Depends(require_scope_and_lga("municipal", "admin"))):
    return await get_daily_collections(request.app.state.pool, lga_id)


@router.post("/snapshot", status_code=201)
async def create_snapshot(request: Request, lga_id: str | None = None, _=Depends(require_scope("admin"))):
    return await append_snapshot(request.app.state.pool, lga_id)


@router.get("/snapshots/{lga_id}")
async def list_snapshots(lga_id: str, request: Request, _=Depends(require_scope_and_lga("municipal", "admin"))):
    return await get_snapshots(request.app.state.pool, lga_id)


@router.get("/snapshots/{lga_id}/verify-chain")
async def verify_chain_endpoint(lga_id: str, request: Request, _=Depends(require_scope_and_lga("municipal", "admin"))):

    return await verify_chain(request.app.state.pool, lga_id)
