"""Text-to-speech via ElevenLabs streaming API.

Preserves the public interface (`tts_token`, `get_audio`) so callers do not change.
Audio bytes are buffered in-process and served by `/telnyx/audio/{token}`.
"""
import hashlib
import logging
import secrets
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MODEL_ID = "eleven_turbo_v2_5"
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (ElevenLabs default demo voice)
OUTPUT_FORMAT = "mp3_44100_128"
TIMEOUT_S = 15.0

_audio_store: dict[str, bytes] = {}
_text_cache: dict[str, str] = {}

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT_S)
    return _client


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

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Accept": "audio/mpeg",
    }
    payload = {"text": text, "model_id": MODEL_ID}
    params = {"output_format": OUTPUT_FORMAT}

    client = _get_client()
    t0 = time.monotonic()
    chunks: list[bytes] = []
    first_byte_at: Optional[float] = None

    async with client.stream("POST", url, headers=headers, json=payload, params=params) as r:
        r.raise_for_status()
        async for chunk in r.aiter_bytes():
            if first_byte_at is None:
                first_byte_at = time.monotonic()
            chunks.append(chunk)

    total_ms = int((time.monotonic() - t0) * 1000)
    ttfb_ms = int((first_byte_at - t0) * 1000) if first_byte_at else -1
    total_bytes = sum(len(c) for c in chunks)
    logger.info(
        "ElevenLabs TTS | ttfb=%dms | total=%dms | bytes=%d | text_len=%d",
        ttfb_ms, total_ms, total_bytes, len(text),
    )
    return b"".join(chunks)
