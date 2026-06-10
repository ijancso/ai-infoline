import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def transcribe_url(recording_url: str) -> Optional[str]:
    from config import settings
    if not settings.deepgram_api_key:
        logger.warning("Nincs DEEPGRAM_API_KEY beállítva")
        return None

    audio_bytes = await _download(recording_url, settings.telnyx_api_key)
    if not audio_bytes:
        return None

    return await _transcribe(audio_bytes, settings.deepgram_api_key)


async def _download(url: str, telnyx_api_key: str) -> Optional[bytes]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("Felvétel letöltési hiba: %s", e)
            return None


async def _transcribe(audio_bytes: bytes, api_key: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&language=hu&smart_format=true",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()
            transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
            logger.info("Deepgram átírás: %s", transcript)
            return transcript or None
        except Exception as e:
            logger.error("Deepgram hiba: %s", e)
            return None
