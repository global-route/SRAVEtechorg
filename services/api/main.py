from contextlib import asynccontextmanager
import asyncpg
import redis.asyncio as aioredis
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, spatial, audit, field, billing, admin, privacy, webhooks
from ledger.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
        min_size=2, max_size=10,
    )
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis-cache:6379"))
    app.state.pool = pool
    app.state.redis = redis
    scheduler = start_scheduler(pool)
    yield
    scheduler.shutdown()
    await pool.close()
    await redis.aclose()


app = FastAPI(title="SRAVE Core API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router,     prefix="/api/v1/auth",    tags=["auth"])
app.include_router(spatial.router,  prefix="/api/v1/spatial", tags=["spatial"])
app.include_router(audit.router,    prefix="/api/v1/audit",   tags=["audit"])
app.include_router(field.router,    prefix="/api/v1/field",   tags=["field"])
app.include_router(billing.router,  prefix="/api/v1/billing", tags=["billing"])
app.include_router(admin.router,    prefix="/api/v1/admin",   tags=["admin"])
app.include_router(privacy.router,  prefix="/api/v1/privacy", tags=["privacy"])
app.include_router(webhooks.router, prefix="/api/v1/billing", tags=["webhooks"])


@app.get("/health", tags=["health"])
async def health():
    db_ok, redis_ok = "ok", "ok"
    try:
        await app.state.pool.fetchval("SELECT 1")
    except Exception:
        db_ok = "error"
    try:
        await app.state.redis.ping()
    except Exception:
        redis_ok = "error"
    return {"status": "ok", "service": "srave-api", "db": db_ok, "redis": redis_ok}
