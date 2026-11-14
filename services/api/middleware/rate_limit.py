import time
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

SCOPE_LIMITS = {
    "municipal":    100,
    "field_agent":  60,
    "multilateral": 20,
    "admin":        500,
    "public":       10,
}
WINDOW = 60  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip health and public endpoints
        if request.url.path in ("/health", "/api/v1/auth/token", "/api/v1/multilateral/verify"):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        # Determine scope from JWT if present (best-effort, no hard failure)
        scope = "public"
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                from jose import jwt
                claims = jwt.decode(
                    auth[7:],
                    os.getenv("JWT_SECRET", ""),
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                scope = claims.get("scope", "public")
            except Exception:
                pass

        limit = SCOPE_LIMITS.get(scope, 10)
        key = f"rl:{scope}:{request.client.host}"
        now = int(time.time())
        window_start = now - WINDOW

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW)
        results = await pipe.execute()
        count = results[2]

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(WINDOW)},
            )
        return await call_next(request)
