import os
from contextlib import asynccontextmanager
from typing import Optional
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from tts.engine import render_text, generate_audio
from whatsapp.sender import upload_media, send_voice_note

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
    structlog.contextvars.bind_contextvars(service="srave-voice-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres-db"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "srave_prod"),
        user=os.getenv("DB_USER", "srave_user"),
        password=os.getenv("DB_PASSWORD"),
        min_size=1, max_size=3,
    )
    app.state.pool = pool
    log.info("startup_complete")
    yield
    await pool.close()
    log.info("shutdown_complete")


app = FastAPI(title="SRAVE Voice Service", version="1.0.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


class VoiceRequest(BaseModel):
    language: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    amount_due_ngn: Optional[float] = None
    payment_link: Optional[str] = None


@app.post("/voice/notice/{assessment_id}")
async def voice_notice(assessment_id: int, body: VoiceRequest):
    row = await app.state.pool.fetchrow(
        """
        SELECT ta.amount_due, ta.payment_ref,
               tr.owner_phone, tr.owner_name, tr.address, tr.owner_language,
               db.lga_id
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        LEFT JOIN tax_roll tr ON tr.lga_id = db.lga_id AND tr.owner_phone = ta.owner_phone
        WHERE ta.id = $1
        """,
        assessment_id,
    )

    language    = body.language      or (row["owner_language"] if row else None) or "yoruba"
    owner_phone = body.owner_phone   or (row["owner_phone"]    if row else None) or ""
    owner_name  = body.owner_name    or (row["owner_name"]     if row else None) or "Property Owner"
    address     = body.address       or (row["address"]        if row else None) or (row["lga_id"] if row else "")
    amount      = body.amount_due_ngn if body.amount_due_ngn is not None else (float(row["amount_due"]) if row else 0.0)
    link        = body.payment_link  or (row["payment_ref"]    if row else None) or ""

    try:
        text = render_text(language=language, owner_name=owner_name,
                           address=address, amount=f"{amount:,.0f}", link=link)
        audio = await generate_audio(text, language)
        if audio and owner_phone:
            media_id = await upload_media(audio)
            await send_voice_note(owner_phone, media_id)
        log.info("voice_notice_dispatched", assessment_id=assessment_id, language=language)
        return {"assessment_id": assessment_id, "voice_status": "dispatched", "language": language}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-voice-service"}
