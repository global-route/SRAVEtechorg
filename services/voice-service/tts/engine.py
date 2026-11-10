import io
import os
from typing import Literal

SUPPORTED = {"yoruba", "igbo", "hausa", "urhobo", "pidgin"}

MMS_LANG_MAP = {
    "yoruba": "yor",
    "igbo":   "ibo",
    "hausa":  "hau",
    "urhobo": "urh",
    "pidgin": "pcm",
}

TEMPLATES = {
    "yoruba":  "Ẹ káàbọ̀, {owner_name}. Ilé rẹ ni {address} ni iye owó orí ilé ₦{amount}. Jọwọ san ní: {link}",
    "igbo":    "Nnọọ, {owner_name}. Ụlọ gị na {address} nwere ụtụ ụlọ ₦{amount}. Biko kwụọ na: {link}",
    "hausa":   "Sannu, {owner_name}. Gidanka a {address} yana da haraji ₦{amount}. Don Allah biya a: {link}",
    "urhobo":  "Miguo, {owner_name}. Unu ọ {address} rẹ tax ọ ₦{amount}. Rọ ẹ vwọ: {link}",
    "pidgin":  "How far, {owner_name}. Your property for {address} get tax of ₦{amount}. Abeg pay here: {link}",
}

_models: dict = {}


def _load_model(language: str):
    if language not in _models:
        from transformers import VitsModel, AutoTokenizer
        import torch
        lang_code = MMS_LANG_MAP[language]
        model_id = f"facebook/mms-tts-{lang_code}"
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir="/models")
        model = VitsModel.from_pretrained(model_id, cache_dir="/models")
        model.eval()
        _models[language] = (tokenizer, model)
    return _models[language]


def render_text(language: str, owner_name: str, address: str, amount: str, link: str) -> str:
    if language not in SUPPORTED:
        raise ValueError(f"Unsupported language: {language}")
    return TEMPLATES[language].format(owner_name=owner_name, address=address, amount=amount, link=link)


async def generate_audio(text: str, language: str) -> bytes:
    import torch
    import soundfile as sf
    from pydub import AudioSegment

    tokenizer, model = _load_model(language)
    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        output = model(**inputs).waveform.squeeze().numpy()

    # Write WAV to buffer
    wav_buf = io.BytesIO()
    sf.write(wav_buf, output, samplerate=model.config.sampling_rate, format="WAV")
    wav_buf.seek(0)

    # Convert WAV → OGG Opus (WhatsApp voice note format)
    audio = AudioSegment.from_wav(wav_buf)
    ogg_buf = io.BytesIO()
    audio.export(ogg_buf, format="ogg", codec="libopus")
    ogg_bytes = ogg_buf.getvalue()

    # Explicitly clear buffers — no disk writes
    wav_buf.close()
    ogg_buf.close()
    return ogg_bytes
