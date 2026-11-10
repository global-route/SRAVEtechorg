import os
from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI
from routers import assess


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
        min_size=1, max_size=5,
    )
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title="SRAVE Billing Worker", version="1.0.0", lifespan=lifespan)
app.include_router(assess.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-billing-worker"}
