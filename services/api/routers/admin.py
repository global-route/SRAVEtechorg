from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from middleware.auth import require_scope

router = APIRouter()


class TaxRates(BaseModel):
    residential_low: float = 30000
    residential_high: float = 80000
    commercial: float = 200000
    industrial: float = 500000


@router.get("/tax-rates/{lga_id}")
async def get_tax_rates(lga_id: str, request: Request, _=Depends(require_scope("admin"))):
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
