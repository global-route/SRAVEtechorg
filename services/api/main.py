from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, spatial, audit, field, billing, admin, privacy, webhooks

app = FastAPI(
    title="SRAVE Core API",
    version="1.0.0",
    description="Spatial Revenue & Asset Verification Engine — Core API",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router,     prefix="/api/v1/auth")
app.include_router(spatial.router,  prefix="/api/v1/spatial",      tags=["spatial"])
app.include_router(audit.router,    prefix="/api/v1/audit",         tags=["audit"])
app.include_router(field.router,    prefix="/api/v1/field",         tags=["field"])
app.include_router(billing.router,  prefix="/api/v1/billing",       tags=["billing"])
app.include_router(admin.router,    prefix="/api/v1/admin",         tags=["admin"])
app.include_router(privacy.router,  prefix="/api/v1/privacy",       tags=["privacy"])
app.include_router(webhooks.router, prefix="/api/v1/billing",       tags=["webhooks"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-api"}
