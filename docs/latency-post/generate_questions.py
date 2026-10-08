#!/usr/bin/env python3
"""Generate 3 fixed English question wavs for the automated test caller.

Run once per project. Writes docs/latency-post/questions/q{1,2,3}.wav as
8 kHz / 16-bit mono WAV (what Telnyx records in and what measure_gaps.py reads).

Requires ELEVENLABS_API_KEY in the environment. One-time cost (~$0.05 total).

The system is currently English-only (Deepgram model=nova-3, language=en), so
the questions are English too. Replace with your own voice later if you want --
run one human-voice round at the end as a sanity check per BRIEF.md.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import wave

import httpx


QUESTIONS = [
    "Hello. What are your opening hours on weekends?",
    "Great. Do you accept credit cards or only cash?",
    "Thanks. One last thing, can I make a reservation for four people this Friday evening?",
]

MODEL_ID = "eleven_turbo_v2_5"
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel, same as tts_service.py
OUTPUT_FORMAT = "pcm_8000"           # 8 kHz 16-bit LE PCM; matches Telnyx recording SR
SAMPLE_RATE = 8000


def _pcm_to_wav(pcm: bytes, sr: int, path: str) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


def _generate(text: str, api_key: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    r = httpx.post(
        url,
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": api_key, "Accept": "audio/pcm"},
        json={"text": text, "model_id": MODEL_ID},
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "questions"))
    args = p.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    for i, text in enumerate(QUESTIONS, 1):
        path = os.path.join(args.out, f"q{i}.wav")
        print(f"[{i}/3] {text!r} -> {path}")
        pcm = _generate(text, api_key)
        _pcm_to_wav(pcm, SAMPLE_RATE, path)
        print(f"      wrote {len(pcm)} PCM bytes ({len(pcm) / 2 / SAMPLE_RATE:.2f} s)")
    print("Done. Serve via /callcontrol/caller/questions/q{1,2,3}.wav once the API is deployed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
