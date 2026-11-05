"""Transport interface contracts (typing.Protocol). Status: SCAFFOLD.

``CongestionController`` is the interface requested in the scaffolding brief. The existing
``CubicController`` (congestion_control.py, copied unchanged) satisfies it structurally and
additionally provides ``on_timeout(now)``, which the reliability layer must call on RTO.

Argument types: ``acked_packets`` / ``lost_packets`` are iterables of objects exposing
``pn`` (int) and ``size`` (bytes); ``rtt_stats`` exposes ``smoothed_rtt`` (seconds) or is a
float. ``pn`` is assumed unique per transmission -- this assumption is part of D14 and must be
reconciled with the final ACK/loss structures before Reliability is implemented.

``TimerHost`` is exactly what ``PacedSender`` uses (``paced_sender.TimerHostLike``):
``time()``, ``call_at(when, cb)`` and ``handle.cancel()``. ``post`` is an addition used for
thread confinement (D11) and is NOT required by PacedSender.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AckedPacket(Protocol):
    pn: int
    size: int


@runtime_checkable
class CongestionController(Protocol):
    """Congestion window + pacing rate state. Never sends, never parses packets."""

    def on_packet_sent(self, pn: int, size: int, now: float) -> None: ...

    def on_ack(self, acked_packets: Iterable[Any], rtt_stats: Any, now: float) -> None: ...

    def on_loss(self, lost_packets: Iterable[Any], now: float) -> None: ...

    def on_persistent_congestion(self) -> None: ...

    def cwnd(self) -> int:
        """Bytes (D6)."""
        ...

    def pacing_rate(self) -> float:
        """Bytes per second (D6). Formula is D5."""
        ...


@runtime_checkable
class TimerHandle(Protocol):
    def cancel(self) -> None:
        """Idempotent; a no-op if the callback already ran."""
        ...


@runtime_checkable
class TimerHost(Protocol):
    """Clock + one-shot timers, all on ONE monotonic clock (seconds)."""

    def time(self) -> float: ...

    def call_at(self, when: float, callback: Callable[[], Any]) -> TimerHandle: ...
