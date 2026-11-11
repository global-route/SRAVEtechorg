from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from ingestion.router import router as ingestion_router
from ai.router import router as ai_router

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
    structlog.contextvars.bind_contextvars(service="srave-spatial-worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    log.info("startup_complete")
    yield
    log.info("shutdown_complete")


app = FastAPI(title="SRAVE Spatial Worker", version="1.0.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(ingestion_router, prefix="/ingestion")
app.include_router(ai_router, prefix="/ai")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-spatial-worker"}
