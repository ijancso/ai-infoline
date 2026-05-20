import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None

# Per-call conversation history cache: call_sid -> list of messages
_sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """Te egy AI-alapú telefonos infoline asszisztens vagy.
Feladatod: segíteni a hívóknak tömör, barátságos és pontos válaszokkal.

Irányelvek:
- Mindig magyarul válaszolj, kivéve ha a hívó más nyelven szólal meg.
- Legyen a válaszod rövid és természetes – ezt szövegfelolvasó (TTS) hangosítja fel.
- Kerüld a felsorolásokat, emojit, csillagokat és egyéb formázást.
- Ha nem tudod a választ, mondd meg őszintén és ajánlj alternatívát.
- Legyél udvarias, de lényegre törő."""


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        import os
        _client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def clear_session(call_sid: str) -> None:
    _sessions.pop(call_sid, None)


async def _load_messages_from_db(db: AsyncSession, call_sid: str) -> list[dict]:
    from models import CallMessage
    result = await db.execute(
        select(CallMessage)
        .where(CallMessage.call_sid == call_sid)
        .order_by(CallMessage.created_at)
    )
    return [{"role": m.role, "content": m.content} for m in result.scalars().all()]


async def _save_turn_to_db(
    db: AsyncSession, call_id: uuid.UUID, call_sid: str, user_input: str, ai_reply: str
) -> None:
    from models import CallMessage
    now = datetime.now(timezone.utc)
    db.add(CallMessage(call_id=call_id, call_sid=call_sid, role="user", content=user_input, created_at=now))
    db.add(CallMessage(
        call_id=call_id, call_sid=call_sid, role="assistant", content=ai_reply,
        created_at=now + timedelta(microseconds=1),
    ))
    await db.commit()


async def get_ai_reply(
    user_input: str,
    call_sid: Optional[str],
    system_prompt: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    call_id: Optional[uuid.UUID] = None,
) -> str:
    client = _get_client()
    session_key = call_sid or "__anonymous__"

    if session_key not in _sessions:
        if db is not None and call_sid:
            _sessions[session_key] = await _load_messages_from_db(db, call_sid)
        else:
            _sessions[session_key] = []

    messages = _sessions[session_key]
    messages.append({"role": "user", "content": user_input})

    effective_prompt = f"{SYSTEM_PROMPT}\n\n{system_prompt}" if system_prompt else SYSTEM_PROMPT

    try:
        t0 = datetime.now(timezone.utc)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": effective_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

        reply = next(
            (block.text for block in response.content if block.type == "text"),
            "Sajnálom, nem tudtam választ generálni.",
        )

        messages.append({"role": "assistant", "content": reply})

        if db is not None and call_sid and call_id is not None:
            await _save_turn_to_db(db, call_id, call_sid, user_input, reply)

        logger.info(
            "Claude válasz | call_sid=%s | %dms | cache_read=%d | in=%d | out=%d",
            call_sid,
            elapsed_ms,
            response.usage.cache_read_input_tokens or 0,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        return reply

    except anthropic.APIError as exc:
        logger.error("Claude API hiba | call_sid=%s | %s", call_sid, exc)
        return "Technikai hiba történt. Kérem, próbálja újra."
