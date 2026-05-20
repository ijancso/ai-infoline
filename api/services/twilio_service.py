import os
from typing import Optional
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Gather


_validator: Optional[RequestValidator] = None


def _get_validator() -> RequestValidator:
    global _validator
    if _validator is None:
        _validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
    return _validator


def verify_twilio_signature(
    signature: Optional[str],
    url: str,
    params: dict,
) -> bool:
    if os.getenv("ENVIRONMENT", "development") == "development":
        return True
    if not signature:
        return False
    try:
        return _get_validator().validate(url, params, signature)
    except Exception:
        return False


def build_greeting_twiml(gather_action: str, caller: Optional[str] = None) -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=gather_action,
        method="POST",
        language="hu-HU",
        speech_timeout="auto",
        enhanced=True,
    )
    gather.say(
        "Üdvözöljük az AI Infoline szolgáltatásban! Miben segíthetünk?",
        language="hu-HU",
    )
    response.append(gather)
    # Ha a hívó nem reagál
    response.redirect(gather_action, method="POST")
    return str(response)


def build_no_input_twiml(gather_action: str) -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=gather_action,
        method="POST",
        language="hu-HU",
        speech_timeout="auto",
        enhanced=True,
    )
    gather.say(
        "Sajnálom, nem hallottam. Kérem, mondja el kérdését!",
        language="hu-HU",
    )
    response.append(gather)
    response.redirect(gather_action, method="POST")
    return str(response)


async def build_response_twiml(
    user_input: str,
    call_sid: Optional[str],
    gather_action: str,
    system_prompt: Optional[str] = None,
    db=None,
    call_id=None,
) -> str:
    from services.claude_service import get_ai_reply
    ai_reply = await get_ai_reply(
        user_input, call_sid, system_prompt, db=db, call_id=call_id
    )

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=gather_action,
        method="POST",
        language="hu-HU",
        speech_timeout="auto",
        enhanced=True,
    )
    gather.say(ai_reply, language="hu-HU")
    response.append(gather)
    response.redirect(gather_action, method="POST")
    return str(response)
