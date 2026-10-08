#!/usr/bin/env python3
"""Parse LATENCY log lines -> results.csv rows.

LATENCY lines (emitted by api/services/latency_debug.py) look like:
  2026-10-08 12:46:14,377 INFO services.latency_debug | LATENCY | \
  ccid=v3:xxx | turn=099a52c0 | stt_done | +1419ms | total=1419ms | len=17

Usage:
  python3 parse_latency.py <logfile|-> --source {emulator,call} \
      --run-id baseline-2026-10-08 --commit <sha> --append results.csv

Turn numbers within one ccid are assigned sequentially (first turn_hex seen
within a ccid becomes turn=1, next becomes turn=2, ...). Call index is NOT in
the CSV schema per BRIEF.md -- group by ccid externally if needed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys


PATTERN = re.compile(
    r"LATENCY \| ccid=(?P<ccid>\S+) \| turn=(?P<turn>\w+) \| "
    r"(?P<stage>[^|]+?)\s*\|\s*\+(?P<delta>\d+)ms\s*\|\s*total=(?P<total>\d+)ms"
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("logfile", help="log file to parse, or - for stdin")
    p.add_argument("--source", choices=("emulator", "call"), required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--commit", default="")
    p.add_argument("--append", required=True, help="results.csv to append to")
    args = p.parse_args()

    stream = sys.stdin if args.logfile == "-" else open(args.logfile)

    rows: list[tuple[str, int, str, int, int]] = []
    turn_map: dict[str, dict[str, int]] = {}

    for line in stream:
        m = PATTERN.search(line)
        if not m:
            continue
        ccid = m.group("ccid")[:24]
        turn_hex = m.group("turn")
        stage = m.group("stage").strip()
        delta = int(m.group("delta"))
        total = int(m.group("total"))

        turns_in_call = turn_map.setdefault(ccid, {})
        if turn_hex not in turns_in_call:
            turns_in_call[turn_hex] = len(turns_in_call) + 1
        turn_idx = turns_in_call[turn_hex]
        rows.append((ccid, turn_idx, stage, delta, total))

    header = ["run_id", "commit", "date", "source", "turn", "stage", "delta_ms", "total_ms"]
    exists = os.path.exists(args.append)
    today = dt.date.today().isoformat()
    with open(args.append, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        for ccid, turn_idx, stage, delta, total in rows:
            w.writerow([args.run_id, args.commit, today, args.source, turn_idx, stage, delta, total])

    print(f"appended {len(rows)} rows from {len(turn_map)} ccid(s) to {args.append}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
