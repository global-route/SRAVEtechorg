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


@router.get("/lga/{lga_id}/forecast")
async def igr_forecast(
    lga_id: str,
    request: Request,
    _=Depends(require_scope_and_lga("municipal", "admin")),
):
    from repository.gap import get_monthly_collections
    monthly = await get_monthly_collections(request.app.state.pool, lga_id)
    if len(monthly) < 3:
        return {"lga_id": lga_id, "error": "Insufficient data — need at least 3 months of collections"}

    import statistics
    values = [m["total_ngn"] for m in monthly]
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)
    slope = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values)) / \
            sum((i - x_mean) ** 2 for i in range(n))
    intercept = y_mean - slope * x_mean

    projections = [
        {"month_offset": i + 1, "projected_ngn": max(0.0, intercept + slope * (n + i))}
        for i in range(12)
    ]
    return {
        "lga_id": lga_id,
        "historical_months": len(monthly),
        "monthly_slope_ngn": round(slope, 2),
        "projections": projections,
    }


@router.get("/benchmarks")
async def lga_benchmarks(
    request: Request,
    _=Depends(require_scope("admin")),
):
    from repository.gap import get_all_lga_benchmarks
    return await get_all_lga_benchmarks(request.app.state.pool)


@router.get("/alerts")
async def list_alerts(
    request: Request,
    resolved: bool = False,
    _=Depends(require_scope("admin")),
):
    rows = await request.app.state.pool.fetch(
        "SELECT id, actor, action, target_id, payload, logged_at FROM audit_log "
        "WHERE action='anomaly_detected' ORDER BY logged_at DESC LIMIT 100"
    )
    return [dict(r) for r in rows]


@router.get("/lga/{lga_id}/reconciliation")
async def reconciliation(
    lga_id: str,
    request: Request,
    format: str = "json",
    _=Depends(require_scope_and_lga("municipal", "admin")),
):
    row = await request.app.state.pool.fetchrow(
        """
        SELECT
            COUNT(*)                                             AS total_assessed,
            COUNT(*) FILTER (WHERE wa_status='delivered')        AS delivered,
            COUNT(*) FILTER (WHERE wa_status='reminder_sent')    AS reminder_sent,
            COUNT(*) FILTER (WHERE wa_status='partially_paid')   AS partially_paid,
            COUNT(*) FILTER (WHERE wa_status='paid')             AS paid,
            COUNT(*) FILTER (WHERE wa_status='escalated')        AS escalated,
            COALESCE(SUM(amount_due), 0)                         AS total_assessed_ngn,
            COALESCE(SUM(amount_paid), 0)                        AS total_collected_ngn,
            COALESCE(SUM(amount_due) - SUM(amount_paid), 0)      AS total_outstanding_ngn
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        WHERE db.lga_id = $1
        """,
        lga_id,
    )
    data = dict(row)
    data["lga_id"] = lga_id

    if format == "csv":
        import csv, io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerow(data)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="reconciliation-{lga_id}.csv"'},
        )
    return data


@router.get("/state/{state_name}/report.pdf", response_class=Response)
async def state_gap_report_pdf(
    state_name: str,
    request: Request,
    _=Depends(require_scope("admin")),
):
    from weasyprint import HTML
    from jinja2 import Template as J2Template

    rows = await request.app.state.pool.fetch(
        """
        SELECT
            db.lga_id,
            COUNT(db.id)                                            AS total_detected,
            COUNT(tr.id)                                            AS registered,
            COALESCE(SUM(ta.amount_paid), 0)                        AS collected_ngn,
            ROUND((COUNT(tr.id)::numeric / NULLIF(COUNT(db.id),0)) * 100, 1) AS formalization_pct
        FROM detected_buildings db
        LEFT JOIN tax_roll tr ON ST_DWithin(db.footprint::geography, tr.geom::geography, 15)
        LEFT JOIN tax_assessments ta ON ta.building_id = db.id
        JOIN lg_boundaries lb ON lb.name = db.lga_id AND lb.state = $1
        WHERE db.verified = true
        GROUP BY db.lga_id ORDER BY formalization_pct DESC NULLS LAST
        """,
        state_name,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for state: {state_name}")

    lgas = [
        {
            "lga_id": r["lga_id"],
            "total_detected": r["total_detected"],
            "registered": r["registered"],
            "collected_ngn": f"{float(r['collected_ngn']):,.0f}",
            "formalization_pct": float(r["formalization_pct"] or 0),
        }
        for r in rows
    ]
    total_detected = sum(r["total_detected"] for r in lgas)
    total_collected = sum(float(r["collected_ngn"].replace(",", "")) for r in lgas)

    html = J2Template("""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
      body{font-family:Arial,sans-serif;font-size:12px;margin:40px}
      h1{color:#166534}table{width:100%;border-collapse:collapse;margin-top:16px}
      th{background:#f0fdf4;padding:8px;text-align:left;font-size:10px;text-transform:uppercase}
      td{padding:8px;border-bottom:1px solid #eee}
    </style></head><body>
    <h1>SRAVE — {{ state_name }} State Revenue Gap Report</h1>
    <p>Generated {{ generated_at }} · {{ lgas|length }} LGAs · Total detected: {{ total_detected|int }} · Total collected: ₦{{ total_collected }}</p>
    <table><thead><tr><th>LGA</th><th>Detected</th><th>Registered</th><th>Collected (NGN)</th><th>Formalization</th></tr></thead>
    <tbody>{% for l in lgas %}<tr><td>{{ l.lga_id }}</td><td>{{ l.total_detected }}</td>
    <td>{{ l.registered }}</td><td>₦{{ l.collected_ngn }}</td><td>{{ l.formalization_pct }}%</td></tr>{% endfor %}
    </tbody></table></body></html>
    """).render(
        state_name=state_name,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        lgas=lgas,
        total_detected=total_detected,
        total_collected=f"{total_collected:,.0f}",
    )
    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="srave-state-{state_name}.pdf"'},
    )


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
