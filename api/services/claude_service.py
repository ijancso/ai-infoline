import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None

# Per-call conversation history: call_sid -> list of messages
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
        _client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
    return _client


def get_session_messages(call_sid: str) -> list[dict]:
    return _sessions.setdefault(call_sid, [])


def clear_session(call_sid: str) -> None:
    _sessions.pop(call_sid, None)


async def get_ai_reply(
    user_input: str,
    call_sid: Optional[str],
    system_prompt: Optional[str] = None,
) -> str:
    client = _get_client()
    session_key = call_sid or "__anonymous__"
    messages = get_session_messages(session_key)

    messages.append({"role": "user", "content": user_input})

    effective_prompt = system_prompt or SYSTEM_PROMPT

    try:
        response = await client.messages.create(
            model="claude-opus-4-7",
            max_tokens=256,
            system=[
                {
                    "type": "text",
                    "text": effective_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        reply = next(
            (block.text for block in response.content if block.type == "text"),
            "Sajnálom, nem tudtam választ generálni.",
        )

        messages.append({"role": "assistant", "content": reply})

        logger.info(
            "Claude válasz | call_sid=%s | cache_read=%d | input_tokens=%d | output_tokens=%d",
            call_sid,
            response.usage.cache_read_input_tokens or 0,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        return reply

    except anthropic.APIError as exc:
        logger.error("Claude API hiba | call_sid=%s | %s", call_sid, exc)
        return "Technikai hiba történt. Kérem, próbálja újra."
