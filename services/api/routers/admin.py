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
