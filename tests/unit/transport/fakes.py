"""Deterministic test doubles: a fake event loop (clock + call_at) and packet types."""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class PacketInfo:
    """Matches the controller's PacketLike protocol (pn, size)."""

    pn: int
    size: int = 1200


@dataclass
class RttStats:
    """Stand-in for the project's RTT estimator (only smoothed_rtt is read)."""

    smoothed_rtt: float | None = 0.1


class FakeHandle:
    def __init__(self, when: float, callback: Callable[[], Any], seq: int) -> None:
        self.when = when
        self.callback = callback
        self.seq = seq
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def __lt__(self, other: FakeHandle) -> bool:
        return (self.when, self.seq) < (other.when, other.seq)


class FakeLoop:
    """Implements the TimerHostLike protocol (time + call_at) with manual time."""

    def __init__(self, start: float = 100.0) -> None:
        self._now = start
        self._heap: list[FakeHandle] = []
        self._seq = 0
        self.call_at_count = 0

    def time(self) -> float:
        return self._now

    def call_at(self, when: float, callback: Callable[[], Any]) -> FakeHandle:
        self._seq += 1
        self.call_at_count += 1
        handle = FakeHandle(when, callback, self._seq)
        heapq.heappush(self._heap, handle)
        return handle

    def pending(self) -> int:
        return sum(1 for h in self._heap if not h.cancelled)

    def next_when(self) -> float | None:
        live = [h.when for h in self._heap if not h.cancelled]
        return min(live) if live else None

    def step(self) -> bool:
        """Run exactly one due (when <= now) timer. Returns False if none was due."""
        while self._heap and self._heap[0].when <= self._now:
            handle = heapq.heappop(self._heap)
            if handle.cancelled:
                continue
            handle.callback()
            return True
        return False

    def advance(self, dt: float) -> None:
        """Move time forward, running every timer that becomes due, in order."""
        target = self._now + dt
        while self._heap and self._heap[0].when <= target:
            handle = heapq.heappop(self._heap)
            if handle.cancelled:
                continue
            self._now = max(self._now, handle.when)
            handle.callback()
        self._now = target


Sent = tuple[float, Any, int]  # (time, packet, packet number)
