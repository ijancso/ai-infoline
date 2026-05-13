from fastapi import APIRouter, Form, Header, HTTPException, Request
from fastapi.responses import Response
from typing import Annotated, Optional

from services.twilio_service import (
    build_greeting_twiml,
    build_gather_twiml,
    build_response_twiml,
    build_no_input_twiml,
    verify_twilio_signature,
)

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
    x_twilio_signature: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    CallStatus: Annotated[Optional[str], Form()] = None,
    CallDuration: Annotated[Optional[str], Form()] = None,
    From: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
):
    """
    Twilio értesít a hívás státuszáról (completed, failed, busy, no-answer).
    Logoljuk és adatbázisba mentjük a hívás adatait.
    """
    await _verify_signature(request, x_twilio_signature)

    if CallStatus in ("completed", "failed", "busy", "no-answer") and CallSid:
        from services.claude_service import clear_session
        clear_session(CallSid)

    # TODO: mentés adatbázisba
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
    """
    Twilio értesít, amikor a felvétel elkészült.
    Letöltjük és DO Spaces-be töltjük fel.
    """
    await _verify_signature(request, x_twilio_signature)

    if RecordingStatus == "completed" and RecordingUrl:
        # TODO: letöltés + Spaces feltöltés
        pass

    return Response(status_code=204)


async def _verify_signature(request: Request, signature: Optional[str]) -> None:
    """Twilio webhook aláírás ellenőrzése (production-ban kötelező)."""
    body = await request.body()
    url = str(request.url)
    if not verify_twilio_signature(signature, url, body):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
