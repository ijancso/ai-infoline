import base64
import hashlib
import logging
import secrets
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TTS_LANGUAGE = "hu-HU"
TTS_VOICE = "hu-HU-Wavenet-A"

_audio_store: dict[str, bytes] = {}
_text_cache: dict[str, str] = {}


async def tts_token(text: str) -> str:
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if text_hash in _text_cache:
        return _text_cache[text_hash]

    audio_bytes = await _generate_audio(text)
    token = secrets.token_urlsafe(12)
    _audio_store[token] = audio_bytes
    _text_cache[text_hash] = token
    return token


def get_audio(token: str) -> Optional[bytes]:
    return _audio_store.get(token)


async def _generate_audio(text: str) -> bytes:
    from config import settings
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": TTS_LANGUAGE, "name": TTS_VOICE},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            json=payload,
            params={"key": settings.google_api_key},
        )
        response.raise_for_status()
    return base64.b64decode(response.json()["audioContent"])
