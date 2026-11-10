from fastapi import APIRouter, Depends
from pydantic import BaseModel
from repository.db import get_pool
from middleware.auth import require_scope

router = APIRouter()


class TaxRates(BaseModel):
    residential_low: float = 30000
    residential_high: float = 80000
    commercial: float = 200000
    industrial: float = 500000


@router.get("/tax-rates/{lga_id}")
async def get_tax_rates(lga_id: str, _=Depends(require_scope("admin"))):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT property_type, annual_rate_ngn FROM tax_rates WHERE lga_id=$1", lga_id
    )
    return {"lga_id": lga_id, "rates": {r["property_type"]: r["annual_rate_ngn"] for r in rows}}


@router.put("/tax-rates/{lga_id}")
async def update_tax_rates(lga_id: str, rates: TaxRates, _=Depends(require_scope("admin"))):
    pool = await get_pool()
    for prop_type, rate in rates.model_dump().items():
        await pool.execute(
            "INSERT INTO tax_rates (lga_id, property_type, annual_rate_ngn) VALUES ($1,$2,$3) "
            "ON CONFLICT (lga_id, property_type) DO UPDATE SET annual_rate_ngn=$3",
            lga_id, prop_type, rate,
        )
    return {"lga_id": lga_id, "updated": rates.model_dump()}
