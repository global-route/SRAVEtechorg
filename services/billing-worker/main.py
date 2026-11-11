import os
from contextlib import asynccontextmanager
import asyncpg
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from routers import assess

log = structlog.get_logger()


def _configure_logging():
    import logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    structlog.contextvars.bind_contextvars(service="srave-billing-worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
        min_size=1, max_size=5,
    )
    app.state.pool = pool
    log.info("startup_complete")
    yield
    await pool.close()
    log.info("shutdown_complete")


app = FastAPI(title="SRAVE Billing Worker", version="1.0.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(assess.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-billing-worker"}
