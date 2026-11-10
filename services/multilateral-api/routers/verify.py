import os
from datetime import datetime, timezone
from fastapi import APIRouter, Query, Request
from signing.signer import sha256_sign, get_public_key_pem
from repository.metrics import get_metrics, get_ocds_export

router = APIRouter()


@router.get("/api/v1/multilateral/verify")
async def verify(request: Request, lga_id: str | None = Query(default=None)):
    metrics = await get_metrics(request.app.state.pool, lga_id)
    payload = {
        "@context": {
            "@vocab": "https://schema.org/",
            "srave": "https://srave.io/vocab#",
            "property_formalization_index": "srave:propertyFormalizationIndex",
            "igr_growth_rate_yoy": "srave:igrGrowthRateYoY",
            "digitized_cadastral_records": "srave:digitizedCadastralRecords",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issuing_authority": "Atlantic Tech Innovations",
        "verified_subnational_entity": lga_id or os.getenv("PILOT_LGA", "Ogun State LGAs"),
        "metrics": {k: v for k, v in metrics.items() if k != "chain_head_hash"},
        "chain_head_hash": metrics["chain_head_hash"],
        "public_key_url": "https://api.srave.io/.well-known/signing-key.pub",
    }
    payload["signature_hash"] = sha256_sign(payload["metrics"])
    return payload


@router.get("/api/v1/multilateral/export/ocds")
async def ocds_export(request: Request, lga_id: str = Query(...)):
    return await get_ocds_export(request.app.state.pool, lga_id)


@router.get("/.well-known/signing-key.pub")
async def public_key():
    return {"public_key": get_public_key_pem()}
