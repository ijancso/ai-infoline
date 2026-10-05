"""Per-turn latency instrumentation. Off by default; set LATENCY_DEBUG=1 to enable.

Emits one log line per stage with call_id/turn_id, delta since previous mark and total
since turn start. Safe to remove: delete this file, revert callers, drop the env var.
"""
import logging
import os
import sys
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

ENABLED: bool = os.getenv("LATENCY_DEBUG", "").lower() in ("1", "true", "yes", "on")

if ENABLED and not logger.handlers and not logging.getLogger().handlers:
    # Standalone (e.g. call_emulator.py) has no logging config; add a stderr handler
    # so LATENCY lines still show up. In the API, main.py's dictConfig runs first and
    # this branch is skipped.
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class TurnTimer:
    __slots__ = ("call_id", "turn_id", "t0", "last")

    def __init__(self, call_id: str, t0: Optional[float] = None, t0_label: Optional[str] = None):
        self.call_id = call_id[:24]
        self.turn_id = uuid.uuid4().hex[:8]
        self.t0 = t0 if t0 is not None else time.monotonic()
        self.last = self.t0
        if ENABLED and t0_label is not None:
            logger.info(
                "LATENCY | ccid=%s | turn=%s | %s | +0ms | total=0ms",
                self.call_id, self.turn_id, t0_label,
            )

    def mark(self, name: str, extra: str = "") -> None:
        if not ENABLED:
            return
        now = time.monotonic()
        delta_ms = int((now - self.last) * 1000)
        total_ms = int((now - self.t0) * 1000)
        self.last = now
        logger.info(
            "LATENCY | ccid=%s | turn=%s | %s | +%dms | total=%dms%s",
            self.call_id,
            self.turn_id,
            name,
            delta_ms,
            total_ms,
            f" | {extra}" if extra else "",
        )


def new_timer(call_id: str, t0: Optional[float] = None, t0_label: Optional[str] = None) -> TurnTimer:
    """Always returns a timer; mark() is a no-op unless LATENCY_DEBUG is set."""
    return TurnTimer(call_id, t0, t0_label)
