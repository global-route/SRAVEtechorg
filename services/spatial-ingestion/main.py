from fastapi import FastAPI
from ingestion.router import router as ingestion_router
from ai.router import router as ai_router

app = FastAPI(title="SRAVE Spatial Ingestion Service", version="1.0.0")

app.include_router(ingestion_router, prefix="/ingestion")
app.include_router(ai_router, prefix="/ai")


@app.get("/health")
def health():
    return {"status": "ok", "service": "srave-spatial-ingestion"}
