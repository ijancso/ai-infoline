import logging
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import Call
from services.call_service import upsert_call
from services.tenant_service import get_tenant_by_phone
from services.telnyx_service import (
    build_greeting_twiml,
    build_response_twiml,
    build_no_input_twiml,
    verify_telnyx_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telnyx", tags=["telnyx"])


def _parse_form(body: bytes) -> dict:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


def _base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{forwarded_proto}://{request.url.netloc}"


async def _verify_signature(body: bytes, request: Request) -> None:
    import os
    if os.getenv("ENVIRONMENT", "development") == "development":
        return
    from config import settings
    signature = request.headers.get("telnyx-signature-ed25519")
    timestamp = request.headers.get("telnyx-timestamp")
    if not verify_telnyx_signature(body, signature, timestamp, settings.telnyx_public_key):
        raise HTTPException(status_code=403, detail="Invalid Telnyx signature")


@router.get("/audio/{token}", summary="Serve TTS audio")
async def audio(token: str):
    from services.tts_service import get_audio
    data = get_audio(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Audio not found")
    return Response(content=data, media_type="audio/mpeg")


@router.post("/voice", summary="Incoming call webhook")
async def voice_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    await _verify_signature(body, request)
    form = _parse_form(body)

    CallSid = form.get("CallSid")
    From = form.get("From")
    To = form.get("To")

    tenant = await get_tenant_by_phone(db, To) if To else None
    if tenant is None:
        logger.warning("Ismeretlen hívott szám | To=%s", To)

    if CallSid:
        await upsert_call(
            db,
            call_sid=CallSid,
            from_number=From,
            to_number=To,
            tenant_id=tenant.id if tenant else None,
        )

    twiml = await build_greeting_twiml(
        gather_action="/telnyx/gather",
        base_url=_base_url(request),
        greeting=tenant.greeting if tenant else None,
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/gather", summary="Speech input webhook")
async def gather_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    await _verify_signature(body, request)
    form = _parse_form(body)

    t0 = time.monotonic()

    CallSid = form.get("CallSid")
    To = form.get("To")
    SpeechResult = form.get("SpeechResult")
    Digits = form.get("Digits")

    base = _base_url(request)

    if not SpeechResult and not Digits:
        twiml = await build_no_input_twiml(
            gather_action="/telnyx/gather",
            base_url=base,
        )
        return Response(content=twiml, media_type="application/xml")

    tenant = await get_tenant_by_phone(db, To) if To else None

    call_id = None
    if CallSid:
        result = await db.execute(select(Call).where(Call.call_sid == CallSid))
        call = result.scalar_one_or_none()
        if call:
            call_id = call.id

    twiml = await build_response_twiml(
        user_input=SpeechResult or Digits,
        call_sid=CallSid,
        gather_action="/telnyx/gather",
        base_url=base,
        system_prompt=tenant.system_prompt if tenant else None,
        db=db,
        call_id=call_id,
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info("Gather kész | call_sid=%s | total=%dms | input=%s", CallSid, elapsed_ms, SpeechResult)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status", summary="Call status callback")
async def status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    await _verify_signature(body, request)
    form = _parse_form(body)

    CallSid = form.get("CallSid")
    CallStatus = form.get("CallStatus")
    CallDuration = form.get("CallDuration")
    From = form.get("From")
    To = form.get("To")

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
