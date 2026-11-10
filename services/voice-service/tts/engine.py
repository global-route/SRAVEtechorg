import os
from typing import Literal

SUPPORTED = {"yoruba", "igbo", "hausa", "urhobo", "pidgin"}

TEMPLATES = {
    "yoruba":  "Ẹ káàbọ̀, {owner_name}. Ilé rẹ ni {address} ni iye owó orí ilé ₦{amount}. Jọwọ san ní: {link}",
    "igbo":    "Nnọọ, {owner_name}. Ụlọ gị na {address} nwere ụtụ ụlọ ₦{amount}. Biko kwụọ na: {link}",
    "hausa":   "Sannu, {owner_name}. Gidanka a {address} yana da haraji ₦{amount}. Don Allah biya a: {link}",
    "urhobo":  "Miguo, {owner_name}. Unu ọ {address} rẹ tax ọ ₦{amount}. Rọ ẹ vwọ: {link}",
    "pidgin":  "How far, {owner_name}. Your property for {address} get tax of ₦{amount}. Abeg pay here: {link}",
}


def render_text(language: str, owner_name: str, address: str, amount: str, link: str) -> str:
    if language not in SUPPORTED:
        raise ValueError(f"Unsupported language: {language}")
    return TEMPLATES[language].format(
        owner_name=owner_name, address=address, amount=amount, link=link
    )


async def generate_audio(text: str, language: str) -> bytes:
    # TODO: load facebook/mms-tts-{lang} model, run inference, return OGG Opus bytes
    # Stub returns empty bytes until models are mounted
    return b""
