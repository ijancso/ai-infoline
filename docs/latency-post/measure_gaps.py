#!/usr/bin/env python3
"""Measure perceived latency from a dual-channel call recording.

Usage:
    python3 measure_gaps.py <wav_file> [--caller-channel {0,1}] [--commit SHA]
                            [--run-id ID] [--append results.csv]

Assumes 8 kHz / 16-bit linear PCM dual-channel wav (Telnyx record_start default
with channels=dual, format=wav). Detects utterances per channel with an RMS
threshold and hangover, then pairs each caller-utterance end with the next
AI-utterance start. Emits one `perceived_total` CSV row per gap.

Validate the caller-channel choice by ear on the first recording (Audacity).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import struct
import sys
import wave
from dataclasses import dataclass
from typing import Iterable


FRAME_MS = 20
HANGOVER_START_MS = 60    # need 60ms of speech frames to start an utterance
HANGOVER_END_MS = 200     # need 200ms of silence frames to end it


@dataclass
class Segment:
    start_ms: int
    end_ms: int


def _rms_frames(samples: list[int], sr: int, frame_ms: int = FRAME_MS) -> list[float]:
    frame_len = sr * frame_ms // 1000
    out: list[float] = []
    for i in range(0, len(samples) - frame_len + 1, frame_len):
        acc = 0
        for s in samples[i : i + frame_len]:
            acc += s * s
        out.append(math.sqrt(acc / frame_len))
    return out


def _detect_segments(rms: list[float], frame_ms: int = FRAME_MS) -> list[Segment]:
    if not rms:
        return []
    sorted_rms = sorted(rms)
    # 10th-pct approximates the quiet-channel noise floor; median overshoots when
    # a channel is >50% signal (e.g. the AI's reply dominates its own track).
    noise_floor = sorted_rms[int(len(sorted_rms) * 0.10)]
    peak = sorted_rms[int(len(sorted_rms) * 0.95)]
    threshold = max(noise_floor * 3.0, peak * 0.1, 150.0)

    start_frames_needed = HANGOVER_START_MS // frame_ms
    end_frames_needed = HANGOVER_END_MS // frame_ms

    segments: list[Segment] = []
    in_speech = False
    seg_start = 0
    speech_run = 0
    silence_run = 0
    for idx, r in enumerate(rms):
        if r > threshold:
            if not in_speech:
                speech_run += 1
                if speech_run >= start_frames_needed:
                    in_speech = True
                    seg_start = (idx - speech_run + 1) * frame_ms
                    silence_run = 0
            else:
                silence_run = 0
        else:
            if in_speech:
                silence_run += 1
                if silence_run >= end_frames_needed:
                    seg_end = (idx - silence_run + 1) * frame_ms
                    segments.append(Segment(seg_start, seg_end))
                    in_speech = False
                    speech_run = 0
            else:
                speech_run = 0
    if in_speech:
        segments.append(Segment(seg_start, len(rms) * frame_ms))
    return segments


def _load_dual(path: str) -> tuple[int, list[int], list[int]]:
    with wave.open(path, "rb") as w:
        n_channels = w.getnchannels()
        sr = w.getframerate()
        sampwidth = w.getsampwidth()
        n_frames = w.getnframes()
        raw = w.readframes(n_frames)
    if n_channels != 2:
        raise SystemExit(f"Expected dual-channel wav, got {n_channels} channels")
    if sampwidth != 2:
        raise SystemExit(f"Expected 16-bit PCM, got sampwidth={sampwidth}")
    interleaved = struct.unpack(f"<{n_frames * 2}h", raw)
    left = list(interleaved[0::2])
    right = list(interleaved[1::2])
    return sr, left, right


def _pair_gaps(caller: list[Segment], ai: list[Segment]) -> list[tuple[Segment, Segment, int]]:
    pairs: list[tuple[Segment, Segment, int]] = []
    ai_idx = 0
    for u in caller:
        while ai_idx < len(ai) and ai[ai_idx].start_ms <= u.end_ms:
            ai_idx += 1
        if ai_idx >= len(ai):
            break
        reply = ai[ai_idx]
        pairs.append((u, reply, reply.start_ms - u.end_ms))
    return pairs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("wav")
    p.add_argument("--caller-channel", type=int, choices=(0, 1), default=0,
                   help="0 = left (default), 1 = right. Verify by ear on the first recording.")
    p.add_argument("--commit", default="")
    p.add_argument("--run-id", default="")
    p.add_argument("--append", default="", help="results.csv to append rows to")
    args = p.parse_args(argv)

    sr, left, right = _load_dual(args.wav)
    channels = (left, right)
    caller_samples = channels[args.caller_channel]
    ai_samples = channels[1 - args.caller_channel]

    caller_segs = _detect_segments(_rms_frames(caller_samples, sr))
    ai_segs = _detect_segments(_rms_frames(ai_samples, sr))

    print(f"caller segments ({len(caller_segs)}):")
    for s in caller_segs:
        print(f"  {s.start_ms:6d} - {s.end_ms:6d} ms  ({s.end_ms - s.start_ms} ms)")
    print(f"ai segments ({len(ai_segs)}):")
    for s in ai_segs:
        print(f"  {s.start_ms:6d} - {s.end_ms:6d} ms  ({s.end_ms - s.start_ms} ms)")

    pairs = _pair_gaps(caller_segs, ai_segs)
    print("\nperceived gaps (caller end -> next AI start):")
    for i, (u, r, gap) in enumerate(pairs, 1):
        print(f"  turn {i}: caller end {u.end_ms} ms -> AI start {r.start_ms} ms  = {gap} ms")

    if args.append and pairs:
        header = ["run_id", "commit", "date", "source", "turn", "stage", "delta_ms", "total_ms"]
        exists = os.path.exists(args.append)
        run_id = args.run_id or os.path.basename(args.wav).rsplit(".", 1)[0]
        today = dt.date.today().isoformat()
        with open(args.append, "a", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(header)
            for i, (_u, _r, gap) in enumerate(pairs, 1):
                w.writerow([run_id, args.commit, today, "recording", i, "perceived_total", gap, gap])
        print(f"\nappended {len(pairs)} rows to {args.append}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
