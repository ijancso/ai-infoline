#!/usr/bin/env python3
"""Place N automated test calls to the AI test number, sequentially.

Guardrails (hard, do not relax without explicit sign-off):
  - Dials only $AI_TEST_NUMBER.
  - Max 20 calls per run.
  - Sequential, with --pause seconds between calls.
  - Prints an estimated cost and asks for confirmation (unless --yes).

Telnyx side (configure once, see docs/latency-post/BRIEF.md step B):
  * A second Call Control Application in the same Telnyx account, with its
    webhook URL set to https://infoline.dev/callcontrol/caller/events.
  * A second Telnyx phone number assigned to that application. This is the
    "from" number used to dial the AI.
  * The usual AI test number stays bound to the primary Call Control
    Application pointing at /callcontrol/events -- do not touch it.

Required environment:
  TELNYX_API_KEY               -- account-level v2 API key (works for both apps).
  TELNYX_CALLER_CONNECTION_ID  -- the connection_id of the 2nd Call Control App.
  TELNYX_CALLER_FROM           -- the 2nd Telnyx number (E.164).
  AI_TEST_NUMBER               -- the AI test number to dial (E.164).

The script only initiates calls. Everything else (greeting wait, question
playback, hangup) is driven by the caller webhook router in
api/routers/callcontrol_caller.py.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import httpx


HARD_MAX_CALLS = 20
# Telnyx HU pricing (verified by user 2026-10-08, 60/60 billing i.e. per-minute rounding):
#   outbound HU->HU Fixed: 0.009, Mobile: 0.015, NGN: 0.03 USD/min
#   inbound HU: 0.006 USD/min
# AI test number +36-1-211-4244 is Budapest landline (area code "1") -> Fixed.
# Per call we pay BOTH legs on Telnyx: outbound (caller) + inbound (AI).
# At 2 billed minutes/call: (0.009 + 0.006) * 2 = 0.030 USD/call.
# Safe upper bound for non-Fixed destinations (Mobile/NGN) is ~0.08 USD/call.
EST_COST_PER_CALL_USD = 0.03


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"ERROR: missing env var {name}", file=sys.stderr)
        sys.exit(2)
    return v


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--pause", type=float, default=30.0, help="seconds between calls")
    p.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    args = p.parse_args()

    if args.count > HARD_MAX_CALLS:
        print(f"ERROR: --count={args.count} exceeds hard max {HARD_MAX_CALLS}", file=sys.stderr)
        return 2
    if args.count <= 0:
        print("ERROR: --count must be positive", file=sys.stderr)
        return 2

    api_key = _env("TELNYX_API_KEY")
    conn_id = _env("TELNYX_CALLER_CONNECTION_ID")
    from_num = _env("TELNYX_CALLER_FROM")
    to_num = _env("AI_TEST_NUMBER")

    est = args.count * EST_COST_PER_CALL_USD
    print(f"About to place {args.count} test call(s):")
    print(f"  from: {from_num}  ->  to: {to_num}")
    print(f"  pause between calls: {args.pause}s")
    print(f"  estimated cost: ~${est:.2f} (${EST_COST_PER_CALL_USD:.3f}/call x {args.count}, HU Fixed, 2 billed min/call)")
    if not args.yes:
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return 1

    for i in range(args.count):
        body = {
            "connection_id": conn_id,
            "to": to_num,
            "from": from_num,
        }
        r = httpx.post(
            "https://api.telnyx.com/v2/calls",
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if not r.is_success:
            print(f"[{i+1}/{args.count}] FAILED: {r.status_code} {r.text[:200]}")
        else:
            ccid = r.json().get("data", {}).get("call_control_id", "")
            print(f"[{i+1}/{args.count}] dialed, ccid={ccid[:24]}...")
        if i < args.count - 1:
            time.sleep(args.pause)

    print("Done. Recordings land in ./recordings/ once each call ends (webhook-driven).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
