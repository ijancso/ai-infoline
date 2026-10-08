"""Webhook + playback orchestration for the automated test-caller leg.

Deliberately separate from `callcontrol.py` so test calls can never route into
the AI handler. Set up a second Telnyx Call Control Application pointing its
webhook at /callcontrol/caller/events, dial from a dedicated second number, and
only the AI test number as the destination.

State machine per call (outbound leg):
  call.answered -> wait 6s for AI greeting -> play q1 -> ... -> hangup after q3.
Fixed waits (not silence detection) keep orchestration simple and reliable; the
actual latency numbers come from measure_gaps.py offline on the dual-channel
recording, not from timings observed here.
"""
import asyncio
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/callcontrol/caller", tags=["callcontrol_caller"])

BASE_URL = "https://infoline.dev"
QUESTIONS_DIR = os.environ.get("LATENCY_QUESTIONS_DIR", "/app/questions")

GREETING_WAIT_S = 8.0  # time to let the AI's greeting play before question 1
REPLY_WAIT_S = 10.0    # max time to let the AI reply before next question
NUM_QUESTIONS = 3

_sessions: dict[str, dict] = {}


async def _safe(coro, name: str, ccid: str):
    try:
        await coro
    except Exception as e:
        logger.error("caller task %s failed | ccid=%.24s | %s: %s", name, ccid, type(e).__name__, e)


@router.get("/questions/{name}")
async def serve_question(name: str):
    """Serve pre-generated question wavs to Telnyx. Public read-only, test wavs only."""
    if "/" in name or ".." in name or not name.endswith(".wav"):
        return JSONResponse({"error": "bad name"}, status_code=400)
    path = os.path.join(QUESTIONS_DIR, name)
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="audio/wav")


@router.post("/events")
async def caller_events(request: Request):
    body = await request.json()
    data = body.get("data", {})
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    ccid: str = payload.get("call_control_id", "")

    logger.info("CALLER event: %s | ccid=%.24s", event_type, ccid)

    if event_type == "call.initiated" and payload.get("direction") == "outgoing":
        _sessions[ccid] = {"q_idx": 0}

    elif event_type == "call.answered":
        _sessions.setdefault(ccid, {"q_idx": 0})
        asyncio.create_task(_safe(_run_script(ccid), "run_script", ccid))

    elif event_type == "call.hangup":
        _sessions.pop(ccid, None)

    return JSONResponse({"status": "ok"})


async def _run_script(ccid: str):
    """Linear script: greeting-wait -> q1 -> reply-wait -> q2 -> ... -> hangup."""
    from services.callcontrol_service import hangup, play_audio, record_start

    await record_start(ccid, channels="dual", fmt="wav")
    await asyncio.sleep(GREETING_WAIT_S)

    for idx in range(1, NUM_QUESTIONS + 1):
        if ccid not in _sessions:
            return
        url = f"{BASE_URL}/callcontrol/caller/questions/q{idx}.wav"
        logger.info("CALLER play q%d | ccid=%.24s | url=%s", idx, ccid, url)
        await play_audio(ccid, url, client_state=f"q_{idx}")
        _sessions[ccid]["q_idx"] = idx
        await asyncio.sleep(REPLY_WAIT_S)

    logger.info("CALLER script done, hanging up | ccid=%.24s", ccid)
    await hangup(ccid)
