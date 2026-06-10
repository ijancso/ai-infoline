#!/usr/bin/env python3
"""
Interaktív hívás emulátor – méri a Claude + TTS latenciát valódi telefon nélkül.

Használat:
    cd /home/jancso/ai-infoline
    python call_emulator.py

Opcionálisan megnyitja az MP3 választ lejátszásra (mpv/ffplay/aplay kell).
"""

import asyncio
import os
import sys
import time
import tempfile
import subprocess
import shutil

# Az api/ mappa importálható legyen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))
_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(_root, "api"))

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, ".env"))

# Lazy import – a settings betöltés az importkor fut
from services.claude_service import get_streaming_tts_token
from services.tts_service import get_audio

BOLD  = "\033[1m"
GREEN = "\033[32m"
CYAN  = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"
DIM   = "\033[2m"

PLAYER = next(
    (p for p in ["mpv", "ffplay", "aplay", "paplay"] if shutil.which(p)),
    None,
)


def _ms(seconds: float) -> str:
    return f"{int(seconds * 1000)} ms"


async def run_turn(text: str, session_id: str, play_audio: bool) -> None:
    print()

    t0 = time.monotonic()
    token, reply = await get_streaming_tts_token(
        user_input=text,
        call_sid=session_id,
        system_prompt=None,
        db=None,
        call_id=None,
    )
    total_ms = time.monotonic() - t0
    audio_bytes = get_audio(token)

    # Kiírás
    print(f"{BOLD}{GREEN}Válasz:{RESET} {reply}")
    print()
    print(f"{DIM}  {BOLD}Összesen: {_ms(total_ms)}{RESET}  (Claude stream + TTS párhuzamosan)")


    # Audio lejátszás
    if play_audio and audio_bytes and PLAYER:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        cmd = {
            "mpv":    ["mpv", "--really-quiet", tmp],
            "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp],
            "aplay":  ["aplay", "-q", tmp],
            "paplay": ["paplay", tmp],
        }[PLAYER]
        subprocess.run(cmd, check=False)
        os.unlink(tmp)
    elif play_audio and not PLAYER:
        print(f"{YELLOW}  (Nincs audio lejátszó – telepíts mpv-t a hanghoz){RESET}")


async def main() -> None:
    play_audio = "--no-audio" not in sys.argv
    session_id = f"emulator-{int(time.time())}"

    print(f"{BOLD}AI Infoline – hívás emulátor{RESET}")
    print(f"{DIM}Kilépés: Ctrl+C vagy üres sor{RESET}")
    if PLAYER:
        print(f"{DIM}Audio lejátszó: {PLAYER}  (--no-audio kapcsolóval kikapcsolható){RESET}")
    print()

    while True:
        try:
            text = input(f"{CYAN}Te:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nViszlát!")
            break

        if not text:
            break

        await run_turn(text, session_id, play_audio)
        print()


if __name__ == "__main__":
    asyncio.run(main())
