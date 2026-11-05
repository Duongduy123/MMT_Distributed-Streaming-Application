"""Reference send gate: congestion window + pacer + priority, one timer.

The design document has a single send scheduler per process that asks each
connection "what may go out now?". This module is that per-connection gate. It
is deliberately small so the team can either use it as is or port the order of
checks in :meth:`PacedSender._run` into the real scheduler.

What it does NOT do: build packets, assign packet numbers, track bytes in
flight, retransmit, or enforce flow control. Those are supplied through
callbacks (``transmit``, ``bytes_in_flight``, ``flow_allows``).

Eligibility, checked in this order for the highest-priority queued packet:

1. flow-control credit (``flow_allows``);
2. ``bytes_in_flight + size <= cwnd`` (skipped for ACK-only packets);
3. pacing tokens (skipped for ACK-only packets).

The gate stops at the first blocked packet instead of skipping ahead, so a
blocked chat packet is never overtaken by file data.

Priority classes are neutral (CONTROL / INTERACTIVE / BULK) because the
transport layer must not know about chat or files; the application layer
maps chat -> INTERACTIVE and file chunks -> BULK.
"""

from __future__ import annotations

import enum
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .congestion_control import CubicController
from .pacer import Pacer

__all__ = [
    "OutgoingPacket",
    "PacedSender",
    "PriorityPacketQueue",
    "SendPriority",
    "TimerHandleLike",
    "TimerHostLike",
]


class SendPriority(enum.IntEnum):
    """Lower value = sent first."""

    CONTROL = 0  # handshake, ACK-only, flow-control updates, stream 0
    INTERACTIVE = 1  # chat conversations
    BULK = 2  # file chunks


@dataclass
class OutgoingPacket:
    """Scheduler-visible metadata of a packet waiting to be sent."""

    size: int
    priority: SendPriority
    # False for ACK-only packets: not in bytes_in_flight, exempt from cwnd & pacing.
    congestion_controlled: bool = True
    payload: Any = None


class PriorityPacketQueue:
    """One FIFO per priority class. FIFO keeps per-stream ordering intact."""

    def __init__(self) -> None:
        self._queues: dict[SendPriority, deque[OutgoingPacket]] = {
            p: deque() for p in SendPriority
        }

    def push(self, packet: OutgoingPacket) -> None:
        self._queues[packet.priority].append(packet)

    def peek(self) -> OutgoingPacket | None:
        for priority in SendPriority:
            if self._queues[priority]:
                return self._queues[priority][0]
        return None

    def pop(self) -> OutgoingPacket | None:
        for priority in SendPriority:
            if self._queues[priority]:
                return self._queues[priority].popleft()
        return None

    def __len__(self) -> int:
        return sum(len(q) for q in self._queues.values())


class TimerHandleLike(Protocol):
    def cancel(self) -> None: ...


class TimerHostLike(Protocol):
    """``asyncio.AbstractEventLoop`` satisfies this (``time`` and ``call_at``)."""

    def time(self) -> float: ...

    def call_at(self, when: float, callback: Callable[[], Any]) -> TimerHandleLike: ...


class PacedSender:
    """Per-connection gate. Owns at most one timer, re-armed on every state change."""

    def __init__(
        self,
        congestion: CubicController,
        pacer: Pacer,
        queue: PriorityPacketQueue,
        transmit: Callable[[OutgoingPacket], int | None],
        bytes_in_flight: Callable[[], int],
        loop: TimerHostLike,
        flow_allows: Callable[[OutgoingPacket], bool] | None = None,
        max_burst_packets: int = 10,
        timer_granularity: float = 0.001,
    ) -> None:
        self._cc = congestion
        self._pacer = pacer
        self._queue = queue
        self._transmit = transmit
        self._bytes_in_flight = bytes_in_flight
        self._loop = loop
        self._flow_allows = flow_allows or (lambda _pkt: True)
        self._max_burst = max_burst_packets
        # asyncio timers are only ~1 ms accurate; waiting at least this long lets a
        # few tokens accumulate so we send a small batch instead of spinning.
        self._granularity = timer_granularity
        self._handle: TimerHandleLike | None = None
        self._handle_when: float | None = None
        self._running = False
        self._closed = False

    @property
    def timer_armed(self) -> bool:
        return self._handle is not None

    def kick(self) -> None:
        """Re-evaluate now. Call after: enqueue, ACK/loss/timeout (cc state changed),
        flow-control credit arriving. Cheap and idempotent."""
        self._run()

    def close(self) -> None:
        """Cancel the timer; the gate never sends again."""
        self._closed = True
        self._cancel_timer()

    # ---------------------------------------------------------------- internals

    def _run(self) -> None:
        if self._closed or self._running:
            return
        self._running = True
        try:
            now = self._loop.time()
            # Pick up the controller's latest rate; tokens earned so far are
            # settled at the previous rate inside set_rate().
            self._pacer.set_rate(self._cc.pacing_rate(), now)
            wake_at: float | None = None
            sent = 0
            while True:
                pkt = self._queue.peek()
                if pkt is None:
                    break  # empty queue: no timer, no spinning
                if not self._flow_allows(pkt):
                    break  # woken by kick() when credit arrives
                controlled = pkt.congestion_controlled
                if controlled and self._bytes_in_flight() + pkt.size > self._cc.cwnd():
                    break  # woken by kick() when an ACK frees window
                if sent >= self._max_burst:
                    wake_at = now  # yield to the event loop, continue next turn
                    break
                if controlled and not self._pacer.try_consume(pkt.size, now):
                    delay = self._pacer.time_until_ready(pkt.size, now)
                    if delay is not None:
                        wake_at = now + max(delay, self._granularity)
                    break
                self._queue.pop()
                pn = self._transmit(pkt)
                sent += 1
                if controlled:
                    if pn is None:
                        raise ValueError("transmit() must return the packet number")
                    self._cc.on_packet_sent(pn, pkt.size, now)
            self._set_timer(wake_at)
        finally:
            self._running = False

    def _on_timer(self) -> None:
        self._handle = None
        self._handle_when = None
        self._run()

    def _set_timer(self, when: float | None) -> None:
        if when is None:
            self._cancel_timer()
            return
        if self._handle is not None and self._handle_when == when:
            return
        self._cancel_timer()
        self._handle = self._loop.call_at(when, self._on_timer)
        self._handle_when = when

    def _cancel_timer(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self._handle = None
        self._handle_when = None
