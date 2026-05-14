import logging

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional

from db import get_db
from services.call_service import upsert_call
from services.twilio_service import (
    build_greeting_twiml,
    build_response_twiml,
    build_no_input_twiml,
    verify_twilio_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])


@router.post("/voice", summary="Incoming call webhook")
async def voice_webhook(
    request: Request,
    x_twilio_signature: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    From: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
    CallStatus: Annotated[Optional[str], Form()] = None,
):
    """
    Twilio hív minket, amikor bejövő hívás érkezik.
    Visszaad egy TwiML választ, amely üdvözli a hívót és elindítja a gather-t.
    """
    await _verify_signature(request, x_twilio_signature)

    twiml = build_greeting_twiml(
        gather_action="/twilio/gather",
        caller=From,
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/gather", summary="Speech/DTMF input webhook")
async def gather_webhook(
    request: Request,
    x_twilio_signature: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    SpeechResult: Annotated[Optional[str], Form()] = None,
    Confidence: Annotated[Optional[str], Form()] = None,
    Digits: Annotated[Optional[str], Form()] = None,
):
    """
    Twilio küldi a felismert szöveget (SpeechResult) vagy DTMF számjegyet (Digits).
    Az AI válaszát TwiML-ként adjuk vissza, majd újra gather-t indítunk.
    """
    await _verify_signature(request, x_twilio_signature)

    if not SpeechResult and not Digits:
        twiml = build_no_input_twiml(gather_action="/twilio/gather")
        return Response(content=twiml, media_type="application/xml")

    user_input = SpeechResult or Digits
    twiml = await build_response_twiml(
        user_input=user_input,
        call_sid=CallSid,
        gather_action="/twilio/gather",
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/status", summary="Call status callback")
async def status_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_twilio_signature: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    CallStatus: Annotated[Optional[str], Form()] = None,
    CallDuration: Annotated[Optional[str], Form()] = None,
    From: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
):
    await _verify_signature(request, x_twilio_signature)

    if CallSid:
        await upsert_call(
            db,
            call_sid=CallSid,
            from_number=From,
            to_number=To,
            status=CallStatus,
            duration_seconds=int(CallDuration) if CallDuration else None,
        )
        if CallStatus in ("completed", "failed", "busy", "no-answer"):
            from services.claude_service import clear_session
            clear_session(CallSid)
        logger.info("Call upserted | call_sid=%s | status=%s", CallSid, CallStatus)

    return Response(status_code=204)


@router.post("/recording", summary="Recording status callback")
async def recording_callback(
    request: Request,
    x_twilio_signature: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    RecordingSid: Annotated[Optional[str], Form()] = None,
    RecordingUrl: Annotated[Optional[str], Form()] = None,
    RecordingStatus: Annotated[Optional[str], Form()] = None,
    RecordingDuration: Annotated[Optional[str], Form()] = None,
):
    await _verify_signature(request, x_twilio_signature)

    if RecordingStatus == "completed" and RecordingUrl and CallSid and RecordingSid:
        from config import settings
        from services.spaces_service import upload_recording

        twilio_auth = (settings.twilio_account_sid, settings.twilio_auth_token)
        try:
            key = await upload_recording(
                recording_url=RecordingUrl,
                call_sid=CallSid,
                recording_sid=RecordingSid,
                twilio_auth=twilio_auth,
            )
            logger.info("Recording saved | call_sid=%s | key=%s", CallSid, key)
        except Exception as exc:
            logger.error("Recording upload failed | call_sid=%s | %s", CallSid, exc)

    return Response(status_code=204)


async def _verify_signature(request: Request, signature: Optional[str]) -> None:
    """Twilio webhook aláírás ellenőrzése (production-ban kötelező)."""
    body = await request.body()
    url = str(request.url)
    if not verify_twilio_signature(signature, url, body):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
