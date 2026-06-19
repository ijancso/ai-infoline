import base64
import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)
_BASE = "https://api.telnyx.com/v2/calls"


def encode_state(state: str) -> str:
    return base64.b64encode(state.encode()).decode()


def decode_state(raw: str) -> str:
    try:
        return base64.b64decode(raw).decode()
    except Exception:
        return raw


async def _post(ccid: str, action: str, body: dict | None = None) -> bool:
    from config import settings
    url = f"{_BASE}/{quote(ccid, safe='')}/actions/{action}"
    logger.info("CC POST %s", url[:80])
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            url,
            json=body or {},
            headers={"Authorization": f"Bearer {settings.telnyx_api_key}"},
        )
    if not r.is_success:
        logger.error("CC %s failed: %s | url=%s | body=%s", action, r.status_code, url[:80], r.text[:400])
    return r.is_success


async def answer(ccid: str) -> bool:
    return await _post(ccid, "answer")


async def play_audio(ccid: str, audio_url: str, client_state: str = "") -> bool:
    body = {"audio_url": audio_url}
    if client_state:
        body["client_state"] = encode_state(client_state)
    return await _post(ccid, "playback_start", body)


async def start_streaming(ccid: str, stream_url: str) -> bool:
    return await _post(ccid, "streaming_start", {
        "stream_url": stream_url,
        "stream_track": "inbound_track",
    })


async def stop_streaming(ccid: str) -> bool:
    return await _post(ccid, "streaming_stop")


async def hangup(ccid: str) -> bool:
    return await _post(ccid, "hangup")
