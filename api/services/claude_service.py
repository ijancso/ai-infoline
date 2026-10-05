import asyncio
import logging
import re
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
- Mindig magyarul válaszolj.
- A hívó magyarul beszél. A hangfelismerő magyar (hu-HU) modellt használ, de az átírásban lehetnek kisebb hibák – értelmezd a legjobb tudásod szerint.
- Írj PONTOSAN KÉT RÖVID mondatot: az első adja a közvetlen választ (max 8 szó), a második egészíti ki (max 10 szó).
- Legyen a válaszod természetes – ezt szövegfelolvasó (TTS) hangosítja fel.
- Kerüld a felsorolásokat, emojit, csillagokat és egyéb formázást."""


def _first_sentence(text: str) -> str:
    """Return only the first sentence for faster TTS. Keeps full text in history."""
    import re
    m = re.search(r'[.!?](?:\s|$)', text)
    if m:
        return text[:m.start() + 1].strip()
    return text.strip()


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


def _build_prompt(system_prompt: Optional[str], knowledge_base: Optional[str]) -> str:
    parts = [SYSTEM_PROMPT]
    if system_prompt:
        parts.append(system_prompt)
    if knowledge_base:
        parts.append(f"## Tudásbázis\n\n{knowledge_base}")
    return "\n\n".join(parts)


async def get_ai_reply(
    user_input: str,
    call_sid: Optional[str],
    system_prompt: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    call_id: Optional[uuid.UUID] = None,
    knowledge_base: Optional[str] = None,
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

    effective_prompt = _build_prompt(system_prompt, knowledge_base)

    try:
        t0 = datetime.now(timezone.utc)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
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

        full_reply = next(
            (block.text for block in response.content if block.type == "text"),
            "Sajnálom, nem tudtam választ generálni.",
        )
        reply = _first_sentence(full_reply)

        messages.append({"role": "assistant", "content": full_reply})

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


async def get_streaming_tts_token(
    user_input: str,
    call_sid: Optional[str],
    system_prompt: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    call_id: Optional[uuid.UUID] = None,
    knowledge_base: Optional[str] = None,
    timer: Optional["object"] = None,
) -> str:
    """Stream Claude, launch TTS on first sentence immediately, cancel stream early.

    Returns a TTS audio token. TTS and DB save run concurrently to minimise latency.
    """
    from services.tts_service import tts_token

    if timer is None:
        from services.latency_debug import ENABLED as _LD_ENABLED, new_timer as _new_timer
        if _LD_ENABLED:
            timer = _new_timer(call_sid or "emu")

    client = _get_client()
    session_key = call_sid or "__anonymous__"

    if session_key not in _sessions:
        if db is not None and call_sid:
            _sessions[session_key] = await _load_messages_from_db(db, call_sid)
        else:
            _sessions[session_key] = []

    messages = _sessions[session_key]
    messages.append({"role": "user", "content": user_input})
    effective_prompt = _build_prompt(system_prompt, knowledge_base)

    t0 = datetime.now(timezone.utc)
    buffer = ""
    first_sentence: Optional[str] = None
    tts_task: Optional[asyncio.Task] = None
    first_token_seen = False

    try:
        if timer is not None:
            timer.mark("llm_request_sent", f"sys_len={len(effective_prompt)} msgs={len(messages)}")
        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            system=[{"type": "text", "text": effective_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        ) as stream:
            async for chunk in stream.text_stream:
                if not first_token_seen:
                    first_token_seen = True
                    if timer is not None:
                        timer.mark("llm_first_token")
                buffer += chunk
                m = re.search(r'[.!?](?:\s|$)', buffer)
                if m:
                    first_sentence = buffer[:m.start() + 1].strip()
                    if timer is not None:
                        timer.mark("llm_done", f"first_sentence_len={len(first_sentence)}")
                    tts_task = asyncio.create_task(tts_token(first_sentence))
                    break  # cancel remaining Claude stream

        if first_sentence is None:
            first_sentence = buffer.strip() or "Sajnálom, nem tudtam válaszolni."
            if first_sentence[-1] not in '.!?':
                first_sentence += '.'
            if timer is not None:
                timer.mark("llm_done", "no_sentence_boundary")
            tts_task = asyncio.create_task(tts_token(first_sentence))

        elapsed_claude_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

        messages.append({"role": "assistant", "content": first_sentence})

        if db is not None and call_sid and call_id is not None:
            await _save_turn_to_db(db, call_id, call_sid, user_input, first_sentence)

        token = await tts_task
        if timer is not None:
            timer.mark("tts_first_audio")
        elapsed_total_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

        logger.info(
            "Claude stream | call_sid=%s | claude=%dms | total=%dms | len=%d",
            call_sid, elapsed_claude_ms, elapsed_total_ms, len(first_sentence),
        )
        return token, first_sentence

    except anthropic.APIError as exc:
        logger.error("Claude stream hiba | call_sid=%s | %s", call_sid, exc)
        fallback = "Technikai hiba történt. Kérem, próbálja újra."
        return await tts_token(fallback), fallback
