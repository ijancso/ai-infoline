import base64
import os
from typing import Optional


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
        f'language="en-US" speechTimeout="1" timeout="8">'
    )


async def build_greeting_twiml(gather_action: str, base_url: str) -> str:
    from services.tts_service import tts_token
    token = await tts_token("Üdvözöljük az AI Infoline szolgáltatásban! Miben segíthetünk?")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f"<Play>{base_url}/telnyx/audio/{token}</Play>"
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )


async def build_no_input_twiml(gather_action: str, base_url: str) -> str:
    from services.tts_service import tts_token
    token = await tts_token("Sajnálom, nem hallottam. Kérem, mondja el kérdését!")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f"<Play>{base_url}/telnyx/audio/{token}</Play>"
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )


async def build_response_twiml(
    user_input: str,
    call_sid: Optional[str],
    gather_action: str,
    base_url: str,
    system_prompt: Optional[str] = None,
    db=None,
    call_id=None,
) -> str:
    from services.claude_service import get_streaming_tts_token
    token, _ = await get_streaming_tts_token(user_input, call_sid, system_prompt, db=db, call_id=call_id)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_gather(gather_action)}"
        f"<Play>{base_url}/telnyx/audio/{token}</Play>"
        "</Gather>"
        f'<Redirect method="POST">{gather_action}</Redirect>'
        "</Response>"
    )
