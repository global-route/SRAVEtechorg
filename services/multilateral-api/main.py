from fastapi import FastAPI
from routers import verify

app = FastAPI(title="SRAVE Multilateral API", version="1.0.0")
app.include_router(verify.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-multilateral-api"}
