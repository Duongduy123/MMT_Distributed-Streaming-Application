"""Token-bucket pacer.

Independent of the congestion controller: it only knows a rate (bytes/second),
a capacity and a clock value passed in by the caller. The caller decides *what*
to send; the pacer only answers "may I send ``size`` bytes now, and if not,
when?". It never sleeps, never starts timers, and never sends.

Rules (design doc, "Pacer"):

* capacity = 10 * MSS (maximum burst: ten full-sized packets);
* tokens accrue at ``rate`` bytes/second and are capped at capacity;
* sending consumes exactly the packet size in tokens;
* the bucket starts full (an initial burst of at most ``capacity`` bytes).

A packet larger than the whole bucket would never be satisfiable, so its cost is
clamped to ``capacity`` (it may go out once the bucket is full and empties it).
"""

from __future__ import annotations

import math

__all__ = ["Pacer"]

_EPS = 1e-9


class Pacer:
    """Token bucket with explicit, monotonic ``now`` arguments (seconds)."""

    def __init__(
        self,
        rate: float,
        now: float,
        mss: int = 1200,
        capacity_packets: int = 10,
    ) -> None:
        if mss <= 0 or capacity_packets <= 0:
            raise ValueError("mss and capacity_packets must be positive")
        self._capacity = float(mss * capacity_packets)
        self._tokens = self._capacity
        self._last = float(now)
        self._rate = 0.0
        self._rate = self._sanitize_rate(rate, fallback=0.0)

    # ------------------------------------------------------------------ queries

    @property
    def capacity(self) -> float:
        """Bucket size in bytes (= maximum burst)."""
        return self._capacity

    @property
    def rate(self) -> float:
        """Current refill rate in bytes/second."""
        return self._rate

    def tokens(self, now: float) -> float:
        """Tokens available at ``now`` (refills first)."""
        self._refill(now)
        return self._tokens

    # ---------------------------------------------------------------- operations

    def set_rate(self, rate: float, now: float) -> None:
        """Change the rate. Tokens earned so far are settled at the *old* rate first.

        Zero is accepted (pacer blocks). Negative / NaN / infinite values are
        ignored and the previous rate is kept, so a bad estimate can neither
        crash the event loop nor open the floodgates.
        """
        self._refill(now)
        self._rate = self._sanitize_rate(rate, fallback=self._rate)

    def can_send(self, size: int, now: float) -> bool:
        """True if ``size`` bytes could be sent right now (does not consume)."""
        self._refill(now)
        return self._tokens + _EPS >= self._cost(size)

    def try_consume(self, size: int, now: float) -> bool:
        """Consume exactly the packet's tokens if available; return whether it did."""
        self._refill(now)
        cost = self._cost(size)
        if self._tokens + _EPS < cost:
            return False
        self._tokens = max(0.0, self._tokens - cost)
        return True

    def time_until_ready(self, size: int, now: float) -> float | None:
        """Seconds until ``size`` bytes can be sent; 0.0 if now; ``None`` if never.

        ``None`` is returned when the rate is zero (or so small the wait is not
        representable): the caller should not arm a timer and should wait for a
        rate change instead.
        """
        self._refill(now)
        missing = self._cost(size) - self._tokens
        if missing <= _EPS:
            return 0.0
        if self._rate <= 0.0:
            return None
        wait = missing / self._rate
        return wait if math.isfinite(wait) else None

    # ---------------------------------------------------------------- internals

    def _cost(self, size: int) -> float:
        valid = (
            isinstance(size, (int, float))
            and not isinstance(size, bool)
            and math.isfinite(size)
            and size >= 0
        )
        if not valid:
            raise ValueError(f"invalid packet size: {size!r}")
        return min(float(size), self._capacity)

    def _refill(self, now: float) -> None:
        if not math.isfinite(now):
            return
        elapsed = now - self._last
        if elapsed <= 0.0:
            return  # same instant, or a clock that went backwards: earn nothing
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last = now

    @staticmethod
    def _sanitize_rate(rate: float, fallback: float) -> float:
        if isinstance(rate, (int, float)) and math.isfinite(rate) and rate >= 0.0:
            return float(rate)
        return fallback
