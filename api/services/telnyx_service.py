import base64
import hashlib
import hmac
import os
import time
from typing import Optional


TTS_LANGUAGE = "hu-HU"
TTS_VOICE = "Google.hu-HU-Standard-A"


def verify_telnyx_signature(
    body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    public_key: Optional[str],
) -> bool:
    if os.getenv("ENVIRONMENT", "development") == "development":
        return True
    if not signature_header or not timestamp_header or not public_key:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        from cryptography.exceptions import InvalidSignature

        signed_payload = f"{timestamp_header}|".encode() + body
        sig_bytes = base64.b64decode(signature_header)
        pub_key_bytes = base64.b64decode(public_key)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)
        pub_key.verify(sig_bytes, signed_payload)
        return True
    except Exception:
        return False


def _gather(action: str) -> str:
    return (
        f'<Gather input="speech" action="{action}" method="POST" '
        f'language="{TTS_LANGUAGE}" speechTimeout="1">'
    )


def build_greeting_twiml(gather_action: str, caller: Optional[str] = None) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f'<Say language="{TTS_LANGUAGE}" voice="{TTS_VOICE}">'
        "Üdvözöljük az AI Infoline szolgáltatásban! Miben segíthetünk?"
        "</Say>"
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )


def build_no_input_twiml(gather_action: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f'<Say language="{TTS_LANGUAGE}" voice="{TTS_VOICE}">'
        "Sajnálom, nem hallottam. Kérem, mondja el kérdését!"
        "</Say>"
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )


async def build_response_twiml(
    user_input: str,
    call_sid: Optional[str],
    gather_action: str,
    system_prompt: Optional[str] = None,
    db=None,
    call_id=None,
) -> str:
    from services.claude_service import get_ai_reply
    ai_reply = await get_ai_reply(user_input, call_sid, system_prompt, db=db, call_id=call_id)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f'<Say language="{TTS_LANGUAGE}" voice="{TTS_VOICE}">{ai_reply}</Say>'
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )
