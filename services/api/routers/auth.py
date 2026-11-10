import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

router = APIRouter()

SECRET = os.getenv("JWT_SECRET", "")
EXPIRY = int(os.getenv("JWT_EXPIRY_SECONDS", 3600))
ALGORITHM = "HS256"

# Scope map — in production replace with DB lookup
_CLIENTS = {
    os.getenv("MUNICIPAL_CLIENT_ID"): ("municipal", os.getenv("MUNICIPAL_CLIENT_SECRET")),
    os.getenv("FIELD_AGENT_CLIENT_ID"): ("field_agent", os.getenv("FIELD_AGENT_CLIENT_SECRET")),
    os.getenv("MULTILATERAL_CLIENT_ID"): ("multilateral", os.getenv("MULTILATERAL_CLIENT_SECRET")),
    os.getenv("ADMIN_CLIENT_ID"): ("admin", os.getenv("ADMIN_CLIENT_SECRET")),
}


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


@router.post("/token")
async def issue_token(body: TokenRequest):
    entry = _CLIENTS.get(body.client_id)
    if not entry or entry[1] != body.client_secret:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    scope, _ = entry
    payload = {
        "sub": body.client_id,
        "scope": scope,
        "exp": datetime.utcnow() + timedelta(seconds=EXPIRY),
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return {"access_token": token, "expires_in": EXPIRY, "token_type": "Bearer"}
