from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tts.engine import render_text, generate_audio
from whatsapp.sender import upload_media, send_voice_note

app = FastAPI(title="SRAVE Voice Service", version="1.0.0")


class VoiceRequest(BaseModel):
    language: str = "yoruba"
    owner_phone: str = ""
    owner_name: str = "Property Owner"
    address: str = ""
    amount_due_ngn: float = 0.0
    payment_link: str = ""


@app.post("/voice/notice/{assessment_id}")
async def voice_notice(assessment_id: str, body: VoiceRequest):
    try:
        text = render_text(
            language=body.language,
            owner_name=body.owner_name,
            address=body.address,
            amount=f"{body.amount_due_ngn:,.0f}",
            link=body.payment_link,
        )
        audio = await generate_audio(text, body.language)
        if audio:
            media_id = await upload_media(audio)
            await send_voice_note(body.owner_phone, media_id)
        return {"assessment_id": assessment_id, "voice_status": "dispatched", "language": body.language}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "srave-voice-service"}
