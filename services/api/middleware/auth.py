import os
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

bearer = HTTPBearer()
SECRET = os.getenv("JWT_SECRET", "")
ALGORITHM = "HS256"


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_scope(*allowed: str):
    def _check(claims: dict = Depends(decode_token)):
        if claims.get("scope") not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return claims
    return _check


def require_scope_and_lga(*allowed: str, lga_param: str = "lga_id"):
    """
    Scope check + LGA tenant isolation.
    Admin scope bypasses the LGA check.
    Municipal/field_agent tokens with a lga_id claim can only access that LGA.
    """
    def _check(request: Request, claims: dict = Depends(decode_token)):
        scope = claims.get("scope")
        if scope not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        if scope != "admin":
            token_lga = claims.get("lga_id")
            route_lga = request.path_params.get(lga_param)
            if token_lga and route_lga and token_lga != route_lga:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="LGA access denied")
        return claims
    return _check
