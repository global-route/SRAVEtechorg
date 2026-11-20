import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from middleware.auth import require_scope, require_scope_and_lga

router = APIRouter()

_VALID_SCOPES = {"municipal", "field_agent", "multilateral", "admin"}


class TaxRates(BaseModel):
    residential_low: float = 30000
    residential_high: float = 80000
    commercial: float = 200000
    industrial: float = 500000


class ClientCreate(BaseModel):
    id: str
    secret: str
    scope: str
    lga_id: str | None = None


# ── Tax rates ────────────────────────────────────────────────────────────────

@router.get("/tax-rates/{lga_id}")
async def get_tax_rates(lga_id: str, request: Request, _=Depends(require_scope_and_lga("admin", "municipal"))):
    rows = await request.app.state.pool.fetch(
        "SELECT property_type, annual_rate_ngn FROM tax_rates WHERE lga_id=$1", lga_id
    )
    return {"lga_id": lga_id, "rates": {r["property_type"]: float(r["annual_rate_ngn"]) for r in rows}}


@router.put("/tax-rates/{lga_id}")
async def update_tax_rates(lga_id: str, rates: TaxRates, request: Request, _=Depends(require_scope("admin"))):
    pool = request.app.state.pool
    for prop_type, rate in rates.model_dump().items():
        await pool.execute(
            "INSERT INTO tax_rates (lga_id, property_type, annual_rate_ngn) VALUES ($1,$2,$3) "
            "ON CONFLICT (lga_id, property_type) DO UPDATE SET annual_rate_ngn=$3",
            lga_id, prop_type, rate,
        )
    return {"lga_id": lga_id, "updated": rates.model_dump()}


# ── Client management ────────────────────────────────────────────────────────

@router.post("/clients", status_code=201)
async def create_client(body: ClientCreate, request: Request, _=Depends(require_scope("admin"))):
    if body.scope not in _VALID_SCOPES:
        raise HTTPException(status_code=422, detail=f"Invalid scope: {body.scope}")
    secret_hash = bcrypt.hashpw(body.secret.encode(), bcrypt.gensalt()).decode()
    await request.app.state.pool.execute(
        "INSERT INTO clients (id, secret_hash, scope, lga_id) VALUES ($1,$2,$3,$4)",
        body.id, secret_hash, body.scope, body.lga_id,
    )
    return {"id": body.id, "scope": body.scope, "lga_id": body.lga_id, "active": True}


@router.get("/clients")
async def list_clients(request: Request, _=Depends(require_scope("admin"))):
    rows = await request.app.state.pool.fetch(
        "SELECT id, scope, lga_id, active, created_at FROM clients ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


@router.delete("/clients/{client_id}", status_code=204)
async def revoke_client(client_id: str, request: Request, _=Depends(require_scope("admin"))):
    result = await request.app.state.pool.execute(
        "UPDATE clients SET active=FALSE WHERE id=$1", client_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Client not found")


# ── LGA settings (confidence threshold) ────────────────────────────────────

class LgaSettings(BaseModel):
    confidence_threshold: float


@router.get("/lga/{lga_id}/settings")
async def get_lga_settings(lga_id: str, request: Request, _=Depends(require_scope("admin"))):
    row = await request.app.state.pool.fetchrow(
        "SELECT confidence_threshold, updated_at FROM lga_settings WHERE lga_id=$1", lga_id
    )
    return {"lga_id": lga_id, "confidence_threshold": float(row["confidence_threshold"]) if row else 0.45}


@router.put("/lga/{lga_id}/settings")
async def update_lga_settings(lga_id: str, body: LgaSettings, request: Request, _=Depends(require_scope("admin"))):
    await request.app.state.pool.execute(
        "INSERT INTO lga_settings (lga_id, confidence_threshold) VALUES ($1,$2) "
        "ON CONFLICT (lga_id) DO UPDATE SET confidence_threshold=$2, updated_at=NOW()",
        lga_id, body.confidence_threshold,
    )
    return {"lga_id": lga_id, "confidence_threshold": body.confidence_threshold}


# ── Enforcement & Escalation ────────────────────────────────────────────────

@router.post("/assessments/{assessment_id}/escalate", status_code=200)
async def escalate_assessment(assessment_id: int, request: Request, _=Depends(require_scope("admin"))):
    row = await request.app.state.pool.fetchrow(
        """
        SELECT ta.id, ta.payment_ref, ta.amount_due, ta.amount_paid, ta.assessed_at,
               ta.owner_phone, tr.owner_name, tr.address, db.lga_id, db.photo_url,
               db.property_type
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        LEFT JOIN tax_roll tr ON tr.owner_phone = ta.owner_phone AND tr.lga_id = db.lga_id
        WHERE ta.id = $1
        """,
        assessment_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")

    await request.app.state.pool.execute(
        "UPDATE tax_assessments SET escalated=TRUE, escalated_at=NOW(), wa_status='escalated' WHERE id=$1",
        assessment_id,
    )

    chain_row = await request.app.state.pool.fetchrow(
        "SELECT ledger_entry_hash FROM audit_snapshots WHERE lga_id=$1 ORDER BY snapshot_date DESC LIMIT 1",
        row["lga_id"],
    )

    import json as _json
    case_file = {
        "assessment_id": assessment_id,
        "payment_ref": row["payment_ref"],
        "owner_name": row["owner_name"],
        "owner_phone": row["owner_phone"],
        "address": row["address"],
        "lga_id": row["lga_id"],
        "property_type": row["property_type"],
        "amount_due": float(row["amount_due"]),
        "amount_paid": float(row["amount_paid"]),
        "outstanding": float(row["amount_due"]) - float(row["amount_paid"]),
        "assessed_at": str(row["assessed_at"]),
        "photo_url": row["photo_url"],
        "audit_chain_hash": chain_row["ledger_entry_hash"] if chain_row else "genesis",
        "escalated_at": "now",
    }
    return {"assessment_id": assessment_id, "status": "escalated", "case_file": case_file}


@router.get("/assessments/{assessment_id}/legal-notice", response_class=None)
async def legal_notice_pdf(assessment_id: int, request: Request, _=Depends(require_scope("admin"))):
    from fastapi.responses import Response
    from weasyprint import HTML
    from jinja2 import Template
    import os as _os
    from datetime import datetime, timezone, timedelta

    row = await request.app.state.pool.fetchrow(
        """
        SELECT ta.payment_ref, ta.amount_due, ta.amount_paid, ta.assessed_at,
               ta.owner_phone, tr.owner_name, tr.address, db.lga_id
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        LEFT JOIN tax_roll tr ON tr.owner_phone = ta.owner_phone AND tr.lga_id = db.lga_id
        WHERE ta.id = $1
        """,
        assessment_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")

    deadline = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%d %B %Y")
    tmpl_path = _os.path.join(_os.path.dirname(__file__), "..", "templates", "legal_demand_notice.html")
    with open(tmpl_path) as f:
        html = Template(f.read()).render(
            ref=row["payment_ref"],
            owner_name=row["owner_name"] or "Property Owner",
            address=row["address"] or row["lga_id"],
            lga_id=row["lga_id"],
            amount_due=f"{float(row['amount_due']):,.0f}",
            amount_paid=f"{float(row['amount_paid']):,.0f}",
            outstanding=f"{float(row['amount_due']) - float(row['amount_paid']):,.0f}",
            deadline=deadline,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="legal-notice-{assessment_id}.pdf"'},
    )


# ── Failed jobs (dead letter queue) ─────────────────────────────────────────

@router.get("/failed-jobs")
async def list_failed_jobs(request: Request, _=Depends(require_scope("admin")),
                           replayed: bool = False, lga_id: str | None = None):
    q = "SELECT id, task_name, job_id, lga_id, error, retries, replayed, failed_at FROM failed_jobs WHERE replayed=$1"
    args: list = [replayed]
    if lga_id:
        q += " AND lga_id=$2"
        args.append(lga_id)
    q += " ORDER BY failed_at DESC LIMIT 100"
    rows = await request.app.state.pool.fetch(q, *args)
    return [dict(r) for r in rows]


@router.post("/failed-jobs/{job_id}/replay", status_code=202)
async def replay_failed_job(job_id: str, request: Request, _=Depends(require_scope("admin"))):
    row = await request.app.state.pool.fetchrow(
        "SELECT task_name, payload, lga_id FROM failed_jobs WHERE job_id=$1 AND replayed=FALSE",
        job_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Failed job not found or already replayed")

    import json
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else dict(row["payload"])

    if row["task_name"] == "ingest_worker.run":
        from services.spatial_worker.ingestion.tasks import run_ingest  # type: ignore
        run_ingest.delay(job_id, row["lga_id"], payload["bbox"],
                         payload.get("source", "Sentinel-2"), payload.get("resolution_m", 1.0))
    elif row["task_name"] == "ai_tasks.run_extraction":
        from services.spatial_worker.ai.tasks import run_extraction  # type: ignore
        run_extraction.delay(job_id, row["lga_id"], payload["tif_path"])
    else:
        raise HTTPException(status_code=422, detail=f"Unknown task: {row['task_name']}")

    await request.app.state.pool.execute(
        "UPDATE failed_jobs SET replayed=TRUE WHERE job_id=$1", job_id
    )
    return {"job_id": job_id, "status": "replayed"}
