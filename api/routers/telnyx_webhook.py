import logging
import time

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional

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


@router.post("/voice", summary="Incoming call webhook")
async def voice_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    telnyx_signature_ed25519: Annotated[Optional[str], Header()] = None,
    telnyx_timestamp: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    From: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
    CallStatus: Annotated[Optional[str], Form()] = None,
):
    await _verify_signature(request, telnyx_signature_ed25519, telnyx_timestamp)

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

    twiml = build_greeting_twiml(gather_action="/telnyx/gather", caller=From)
    return Response(content=twiml, media_type="application/xml")


@router.post("/gather", summary="Speech/DTMF input webhook")
async def gather_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    telnyx_signature_ed25519: Annotated[Optional[str], Header()] = None,
    telnyx_timestamp: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
    SpeechResult: Annotated[Optional[str], Form()] = None,
    Confidence: Annotated[Optional[str], Form()] = None,
    Digits: Annotated[Optional[str], Form()] = None,
):
    await _verify_signature(request, telnyx_signature_ed25519, telnyx_timestamp)

    t0 = time.monotonic()

    if not SpeechResult and not Digits:
        twiml = build_no_input_twiml(gather_action="/telnyx/gather")
        return Response(content=twiml, media_type="application/xml")

    tenant = await get_tenant_by_phone(db, To) if To else None

    call_id = None
    if CallSid:
        result = await db.execute(select(Call).where(Call.call_sid == CallSid))
        call = result.scalar_one_or_none()
        if call:
            call_id = call.id

    user_input = SpeechResult or Digits
    twiml = await build_response_twiml(
        user_input=user_input,
        call_sid=CallSid,
        gather_action="/telnyx/gather",
        system_prompt=tenant.system_prompt if tenant else None,
        db=db,
        call_id=call_id,
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info("Gather kész | call_sid=%s | total=%dms", CallSid, elapsed_ms)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status", summary="Call status callback")
async def status_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    telnyx_signature_ed25519: Annotated[Optional[str], Header()] = None,
    telnyx_timestamp: Annotated[Optional[str], Header()] = None,
    CallSid: Annotated[Optional[str], Form()] = None,
    CallStatus: Annotated[Optional[str], Form()] = None,
    CallDuration: Annotated[Optional[str], Form()] = None,
    From: Annotated[Optional[str], Form()] = None,
    To: Annotated[Optional[str], Form()] = None,
):
    await _verify_signature(request, telnyx_signature_ed25519, telnyx_timestamp)

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


async def _verify_signature(
    request: Request,
    signature: Optional[str],
    timestamp: Optional[str],
) -> None:
    import os
    if os.getenv("ENVIRONMENT", "development") == "development":
        return
    from config import settings
    body = await request.body()
    if not verify_telnyx_signature(body, signature, timestamp, settings.telnyx_public_key):
        raise HTTPException(status_code=403, detail="Invalid Telnyx signature")
