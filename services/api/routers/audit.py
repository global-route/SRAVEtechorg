from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from repository.gap import get_gap_analysis, get_daily_collections
from ledger.chain import append_snapshot, get_snapshots, verify_chain
from middleware.auth import require_scope, require_scope_and_lga
import hashlib, json, os
from datetime import datetime, timezone

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


@router.get("/lga/{lga_id}/report.pdf", response_class=Response)
async def gap_report_pdf(lga_id: str, request: Request, _=Depends(require_scope_and_lga("municipal", "admin"))):
    from weasyprint import HTML
    from string import Template

    gap = await get_gap_analysis(request.app.state.pool, lga_id)
    if not gap:
        raise HTTPException(status_code=404, detail="LGA not found")

    collections = await get_daily_collections(request.app.state.pool, lga_id)

    chain_row = await request.app.state.pool.fetchrow(
        "SELECT ledger_entry_hash FROM audit_snapshots WHERE lga_id=$1 ORDER BY snapshot_date DESC LIMIT 1",
        lga_id,
    )
    chain_head = chain_row["ledger_entry_hash"] if chain_row else "genesis"

    canonical = json.dumps(gap, sort_keys=True, default=str)
    signature = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    tmpl_path = os.path.join(os.path.dirname(__file__), "..", "templates", "gap_report.html")
    with open(tmpl_path) as f:
        raw = f.read()

    # Simple Jinja2-style render
    from jinja2 import Template as J2Template
    html = J2Template(raw).render(
        lga_id=lga_id,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total_detected_buildings=f"{gap['total_detected_buildings']:,}",
        registered_tax_payers=f"{gap['registered_tax_payers']:,}",
        unregistered_gap=f"{gap['unregistered_gap']:,}",
        estimated_annual_revenue_gap_ngn=f"{gap['estimated_annual_revenue_gap_ngn']:,.0f}",
        compliance_percentage=gap["compliance_percentage"],
        collections=[{"date": r["date"], "paid_count": r["paid_count"],
                      "total_ngn": f"{r['total_ngn']:,.0f}"} for r in collections],
        chain_head_hash=chain_head,
        signature=signature,
    )

    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="srave-gap-{lga_id}.pdf"'},
    )
