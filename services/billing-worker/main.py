from fastapi import FastAPI
from routers import assess

app = FastAPI(title="SRAVE Billing Worker", version="1.0.0")
app.include_router(assess.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-billing-worker"}
