import os
from datetime import datetime, timezone
from fastapi import APIRouter
from signing.signer import sha256_sign

router = APIRouter()

DB_URL = os.getenv("DATABASE_URL", "")


@router.get("/api/v1/multilateral/verify")
async def verify():
    # TODO: query real metrics from asyncpg pool
    metrics = {
        "property_formalization_index": 0.0,
        "digitized_cadastral_records": 0,
        "igr_growth_rate_yoy": 0.0,
    }
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
        "verified_subnational_entity": os.getenv("PILOT_LGA", "Ogun State LGAs"),
        "metrics": metrics,
    }
    payload["signature_hash"] = sha256_sign(metrics)
    return payload


@router.get("/.well-known/signing-key.pub")
async def public_key():
    from signing.signer import get_public_key_pem
    return {"public_key": get_public_key_pem()}
