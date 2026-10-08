import asyncio
import base64
import json
import logging
import os
import secrets
import time
from typing import Optional

import httpx
import websockets
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/callcontrol", tags=["callcontrol"])


async def _safe(coro, name: str, ccid: str):
    try:
        await coro
    except Exception as e:
        logger.error("Task %s failed | ccid=%.24s | %s: %s", name, ccid, type(e).__name__, e)

BASE_URL = "https://infoline.dev"

# call_control_id -> session dict
_sessions: dict[str, dict] = {}

# stream_id -> call_control_id (short-lived, cleared on WebSocket accept)
_stream_map: dict[str, str] = {}


@router.post("/events")
async def call_events(request: Request):
    body = await request.json()
    data = body.get("data", {})
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    ccid: str = payload.get("call_control_id", "")

    logger.info("CC event: %s | ccid=%.24s", event_type, ccid)

    if event_type == "call.initiated" and payload.get("direction") == "incoming":
        from services.callcontrol_service import answer
        _sessions[ccid] = {
            "from": payload.get("from"),
            "to": payload.get("to"),
        }
        await answer(ccid)

    elif event_type == "call.answered":
        logger.info("call.answered | ccid in sessions: %s | sessions: %s", ccid in _sessions, list(_sessions.keys())[:3])
        if ccid in _sessions:
            asyncio.create_task(_safe(_on_answered(ccid), "on_answered", ccid))

    elif event_type == "call.playback.ended":
        from services.callcontrol_service import decode_state
        state = decode_state(payload.get("client_state", ""))
        logger.info("Playback ended | state=%s | ccid=%.24s", state, ccid)
        if state in ("greeting", "response", "no_input") and ccid in _sessions:
            asyncio.create_task(_safe(_start_listening(ccid), "start_listening", ccid))

    elif event_type == "call.hangup":
        session = _sessions.pop(ccid, None)
        if session:
            from services.claude_service import clear_session
            clear_session(ccid)
        logger.info("Call ended | ccid=%.24s", ccid)

    elif event_type == "call.recording.saved":
        asyncio.create_task(_safe(_on_recording_saved(ccid, payload), "recording_saved", ccid))

    return JSONResponse({"status": "ok"})


async def _on_answered(ccid: str):
    logger.info("_on_answered start | ccid=%.24s", ccid)
    from config import settings
    from db import AsyncSessionLocal
    from services.callcontrol_service import play_audio, record_start
    from services.tenant_service import get_tenant_by_phone
    from services.tts_service import tts_token

    session = _sessions.get(ccid)
    if not session:
        logger.warning("_on_answered: no session for ccid=%.24s", ccid)
        return

    if settings.record_calls:
        asyncio.create_task(_safe(record_start(ccid), "record_start", ccid))

    async with AsyncSessionLocal() as db:
        tenant = await get_tenant_by_phone(db, session.get("to")) if session.get("to") else None

    if tenant:
        session["system_prompt"] = tenant.system_prompt
        session["knowledge_base"] = tenant.knowledge_base
        session["tenant_id"] = tenant.id

    greeting = (tenant.greeting if tenant else None) or \
        "Welcome to AI Infoline! How can we help you?"

    token = await tts_token(greeting)
    await play_audio(ccid, f"{BASE_URL}/telnyx/audio/{token}", client_state="greeting")


async def _start_listening(ccid: str):
    from services.callcontrol_service import start_streaming
    stream_id = secrets.token_urlsafe(16)
    _stream_map[stream_id] = ccid
    await start_streaming(ccid, f"wss://infoline.dev/callcontrol/stream/{stream_id}")


@router.websocket("/stream/{stream_id}")
async def stream_ws(websocket: WebSocket, stream_id: str):
    ccid = _stream_map.pop(stream_id, None)
    if not ccid or ccid not in _sessions:
        logger.warning("Unknown stream_id: %s", stream_id)
        await websocket.close()
        return

    await websocket.accept()
    logger.info("Stream open | ccid=%.24s", ccid)

    from config import settings
    if not settings.deepgram_api_key:
        logger.error("DEEPGRAM_API_KEY nincs beállítva")
        asyncio.create_task(_play_no_input(ccid))
        return

    dg_url = (
        "wss://api.deepgram.com/v1/listen"
        "?model=nova-3&language=en&encoding=mulaw&sample_rate=8000"
        "&channels=1&endpointing=500&interim_results=true"
        "&utterance_end_ms=1000&smart_format=true"
    )

    transcript: Optional[str] = None
    stt_done_at: Optional[float] = None
    t0 = time.monotonic()

    try:
        async with websockets.connect(
            dg_url,
            additional_headers={"Authorization": f"Token {settings.deepgram_api_key}"},
        ) as dg_ws:

            async def _recv_dg():
                nonlocal transcript, stt_done_at
                fragments: list[str] = []
                async for raw in dg_ws:
                    data = json.loads(raw)
                    if data.get("type") == "UtteranceEnd":
                        if fragments:
                            transcript = " ".join(fragments).strip()
                            stt_done_at = time.monotonic()
                            return
                        continue
                    alts = data.get("channel", {}).get("alternatives", [{}])
                    text = alts[0].get("transcript", "") if alts else ""
                    if data.get("is_final") and text:
                        fragments.append(text)

            dg_task = asyncio.create_task(_recv_dg())

            try:
                while transcript is None:
                    try:
                        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
                    except asyncio.TimeoutError:
                        break
                    msg = json.loads(raw)
                    if msg.get("event") == "media":
                        audio = base64.b64decode(msg["media"]["payload"])
                        await dg_ws.send(audio)
                    elif msg.get("event") == "stop":
                        break
            except (WebSocketDisconnect, Exception) as e:
                logger.debug("Telnyx stream closed: %s", e)

            dg_task.cancel()
            try:
                await dg_task
            except asyncio.CancelledError:
                pass

            try:
                await dg_ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass

    except Exception as e:
        logger.error("Deepgram connection error: %s", e)

    elapsed = int((time.monotonic() - t0) * 1000)
    logger.info("Stream done | ccid=%.24s | %dms | input=%s", ccid, elapsed, transcript)

    if transcript:
        asyncio.create_task(
            _safe(_respond(ccid, transcript, stt_done_at=stt_done_at), "respond", ccid)
        )
    else:
        asyncio.create_task(_safe(_play_no_input(ccid), "play_no_input", ccid))


async def _on_recording_saved(ccid: str, payload: dict):
    """Download dual-channel wav for latency gap measurement (step A of latency-post)."""
    from config import settings

    urls = payload.get("recording_urls") or {}
    url = urls.get("wav") or urls.get("mp3")
    if not url:
        logger.warning("recording.saved without url | ccid=%.24s | payload keys=%s", ccid, list(payload.keys()))
        return

    ext = "wav" if urls.get("wav") else "mp3"
    rec_id = payload.get("recording_id") or secrets.token_hex(6)
    os.makedirs(settings.recordings_dir, exist_ok=True)
    path = os.path.join(settings.recordings_dir, f"{ccid[:24]}_{rec_id}.{ext}")

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)

    logger.info("Recording saved | ccid=%.24s | path=%s | bytes=%d", ccid, path, len(r.content))


async def _play_no_input(ccid: str):
    from services.callcontrol_service import play_audio
    from services.tts_service import tts_token
    token = await tts_token("Sorry, I didn't catch that. Please tell me your question.")
    await play_audio(ccid, f"{BASE_URL}/telnyx/audio/{token}", client_state="no_input")


async def _respond(ccid: str, user_input: str, stt_done_at: Optional[float] = None):
    from db import AsyncSessionLocal
    from models import Call
    from services.call_service import upsert_call
    from services.callcontrol_service import play_audio
    from services.claude_service import get_streaming_tts_token
    from services.latency_debug import new_timer
    from sqlalchemy import select

    session = _sessions.get(ccid)
    if not session:
        return

    t0 = time.monotonic()
    # Recv loop only closes on UtteranceEnd (utterance_end_ms=1000ms silence; DG minimum).
    DG_CLOSE_HOLD_S = 1.0
    speech_end_at = (stt_done_at - DG_CLOSE_HOLD_S) if stt_done_at else t0
    timer = new_timer(
        ccid, t0=speech_end_at, t0_label="speech_end_detected (estimated, DG close hold~1000ms)"
    )
    timer.mark("stt_done", f"len={len(user_input)}")

    async with AsyncSessionLocal() as db:
        await upsert_call(
            db,
            call_sid=ccid,
            from_number=session.get("from"),
            to_number=session.get("to"),
            tenant_id=session.get("tenant_id"),
        )
        result = await db.execute(select(Call).where(Call.call_sid == ccid))
        call = result.scalar_one_or_none()
        call_id = call.id if call else None
        timer.mark("db_ready")

        token, reply = await get_streaming_tts_token(
            user_input=user_input,
            call_sid=ccid,
            system_prompt=session.get("system_prompt"),
            knowledge_base=session.get("knowledge_base"),
            db=db,
            call_id=call_id,
            timer=timer,
        )

    await play_audio(ccid, f"{BASE_URL}/telnyx/audio/{token}", client_state="response")
    timer.mark("audio_sent")

    elapsed = int((time.monotonic() - t0) * 1000)
    logger.info("Response | ccid=%.24s | %dms | %s", ccid, elapsed, reply[:60])
