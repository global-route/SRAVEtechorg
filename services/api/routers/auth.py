import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Request
from jose import jwt
from pydantic import BaseModel

router = APIRouter()

SECRET = os.getenv("JWT_SECRET", "")
EXPIRY = int(os.getenv("JWT_EXPIRY_SECONDS", 3600))
REFRESH_TTL = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", 604800))  # 7 days
ALGORITHM = "HS256"


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _make_access_token(client_id: str, scope: str, lga_id: str | None) -> str:
    payload = {
        "sub": client_id,
        "scope": scope,
        "lga_id": lga_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=EXPIRY),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


@router.post("/token")
async def issue_token(body: TokenRequest, request: Request):
    pool = request.app.state.pool
    row = await pool.fetchrow(
        "SELECT secret_hash, scope, lga_id FROM clients WHERE id=$1 AND active=TRUE",
        body.client_id,
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(body.client_secret.encode(), row["secret_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = _make_access_token(body.client_id, row["scope"], row["lga_id"])

    refresh_token = secrets.token_urlsafe(48)
    redis = request.app.state.redis
    await redis.setex(
        f"refresh:{refresh_token}",
        REFRESH_TTL,
        f"{body.client_id}:{row['scope']}:{row['lga_id'] or ''}",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": EXPIRY,
        "token_type": "Bearer",
    }


@router.post("/refresh")
async def refresh_token(body: RefreshRequest, request: Request):
    redis = request.app.state.redis
    value = await redis.get(f"refresh:{body.refresh_token}")
    if not value:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    parts = value.decode().split(":")
    client_id, scope, lga_id = parts[0], parts[1], parts[2] or None

    # Rotate — delete old, issue new
    await redis.delete(f"refresh:{body.refresh_token}")
    new_refresh = secrets.token_urlsafe(48)
    await redis.setex(
        f"refresh:{new_refresh}",
        REFRESH_TTL,
        f"{client_id}:{scope}:{lga_id or ''}",
    )

    return {
        "access_token": _make_access_token(client_id, scope, lga_id),
        "refresh_token": new_refresh,
        "expires_in": EXPIRY,
        "token_type": "Bearer",
    }
