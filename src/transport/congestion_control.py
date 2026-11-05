"""CUBIC congestion control for the UDP streaming transport.

This module only maintains congestion-control *state*. It never parses
packets, retransmits data, tracks bytes in flight, or sends anything: the
reliability layer reports events (sent / acked / lost / timeout) and the send
scheduler asks :meth:`CubicController.cwnd` and
:meth:`CubicController.pacing_rate` what it may do.

Units (kept explicit because the cubic equation is defined in segments):

* Public API: ``cwnd()`` is **bytes**, ``pacing_rate()`` is **bytes/second**,
  time (``now``) is **seconds** on one monotonic clock (``loop.time()``).
* The cubic / Reno-friendly equations are evaluated in **segments**
  (``bytes / MSS``) with ``t`` in seconds, then converted back to bytes.

Project behaviour vs. RFC 9438
------------------------------
This is the *simplified* CUBIC of the course specification, not full RFC 9438:
no fast convergence, no HyStart, no ``t + RTT`` look-ahead. The Reno-friendly
estimate and the 1.5x per-ACK target cap are taken from the RFC. See
``docs/congestion_control.md``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "CubicConfig",
    "CubicController",
    "PacketLike",
    "RttLike",
    "cubic_k",
    "cubic_window",
    "reno_friendly_alpha",
]

# Guard against float error in floor(cwnd/MSS * beta): e.g. 0.7 * 3 is
# 2.0999999999999996 and a product that should be an integer can land just below it.
_EPS = 1e-9
_MIN_SRTT = 1e-6  # seconds; avoids division by ~0 when an RTT sample is bogus


class PacketLike(Protocol):
    """What the controller needs to know about an acked / lost packet."""

    pn: int  # monotonically increasing packet number, never reused
    size: int  # bytes counted toward bytes_in_flight


class RttLike(Protocol):
    """Subset of the project's RTT estimator used here (seconds)."""

    smoothed_rtt: float | None


@dataclass(frozen=True)
class CubicConfig:
    """Tunable constants. Defaults follow the course specification.

    ``initial_ssthresh_packets=None`` means "infinity" (slow start until loss).
    """

    mss: int = 1200
    beta: float = 0.7
    c: float = 0.4
    initial_cwnd_packets: int = 2
    initial_ssthresh_packets: int | None = 8
    min_cwnd_packets: int = 2  # floor for fast loss / persistent congestion
    timeout_cwnd_packets: int = 1  # cwnd after an RTO (mmt-ass1, section 4)
    max_cwnd_bytes: int = 16 * 1024 * 1024  # sanity cap = max flow-control window
    default_rtt: float = 0.333  # used until the RTT estimator has a sample
    slow_start_pacing_gain: float = 2.0
    ca_pacing_gain: float = 1.2
    # mmt-ass1 writes loss reduction as floor(cwnd * 0.7) in whole packets.
    # False => reduce in bytes (design doc wording: max(cwnd * beta, 2 * MSS)).
    floor_to_mss: bool = True
    # RFC 9438 caps the per-ACK target at 1.5 * cwnd to avoid huge jumps.
    target_cap: float = 1.5

    @classmethod
    def design_doc(cls) -> CubicConfig:
        """Alternative preset: initial cwnd 10*MSS, ssthresh infinity, byte floor."""
        return cls(
            initial_cwnd_packets=10,
            initial_ssthresh_packets=None,
            floor_to_mss=False,
        )


def cubic_k(w_max: float, beta: float, c: float) -> float:
    """K = cbrt(W_max * (1 - beta) / C); ``w_max`` in segments, result in seconds."""
    if not math.isfinite(w_max) or w_max <= 0:
        return 0.0
    return (w_max * (1.0 - beta) / c) ** (1.0 / 3.0)


def cubic_window(t: float, k: float, w_max: float, c: float) -> float:
    """W(t) = C * (t - K)^3 + W_max, in segments. ``t`` in seconds since the epoch."""
    return c * (t - k) ** 3 + w_max


def reno_friendly_alpha(beta: float) -> float:
    """RFC 9438 section 4.3: segments added per RTT, 3 * (1 - beta) / (1 + beta)."""
    return 3.0 * (1.0 - beta) / (1.0 + beta)


class CubicController:
    """CUBIC congestion controller (bytes in, bytes out).

    State machine::

        slow start --cwnd >= ssthresh--> congestion avoidance (cubic epoch)
        any state --fast loss--> congestion avoidance + recovery period
        any state --timeout--> slow start (cwnd = 1 MSS)
        any state --persistent congestion--> slow start (cwnd = 2 MSS)

    A *recovery period* starts at a loss and ends when a packet sent after the
    loss is acknowledged. Inside it the window does not grow and further loss
    reports for older packets do not shrink it again.
    """

    def __init__(self, config: CubicConfig | None = None) -> None:
        self.config = config or CubicConfig()
        cfg = self.config
        self._mss = float(cfg.mss)
        self._cwnd = float(cfg.initial_cwnd_packets * cfg.mss)
        self._ssthresh = (
            math.inf
            if cfg.initial_ssthresh_packets is None
            else float(cfg.initial_ssthresh_packets * cfg.mss)
        )
        self._w_max = 0.0  # bytes; 0 => no loss seen yet
        self._epoch_start: float | None = None
        self._k = 0.0  # seconds
        self._w_est_start = 0.0  # segments at epoch start (Reno-friendly anchor)
        self._largest_sent_pn = -1
        self._recovery_pn = -1  # packets with pn <= this were sent before recovery
        self._in_recovery = False
        self._collapsed = (
            False  # True after timeout/persistent congestion until new ACK
        )
        self._srtt = cfg.default_rtt

    # ------------------------------------------------------------------ queries

    def cwnd(self) -> int:
        """Congestion window in bytes (never below 1 MSS)."""
        return int(self._cwnd)

    def ssthresh(self) -> float:
        """Slow-start threshold in bytes (``math.inf`` if unset)."""
        return self._ssthresh

    def w_max(self) -> float:
        """Pre-loss window in bytes (0 until the first loss/timeout)."""
        return self._w_max

    @property
    def in_slow_start(self) -> bool:
        return self._cwnd < self._ssthresh

    @property
    def in_recovery(self) -> bool:
        return self._in_recovery

    @property
    def epoch_start(self) -> float | None:
        return self._epoch_start

    @property
    def k(self) -> float:
        """Current cubic ``K`` in seconds."""
        return self._k

    def pacing_rate(self) -> float:
        """Bytes per second: 2 * cwnd / srtt in slow start, else 1.2 * cwnd / srtt."""
        gain = (
            self.config.slow_start_pacing_gain
            if self.in_slow_start
            else self.config.ca_pacing_gain
        )
        rate = gain * self._cwnd / max(self._srtt, _MIN_SRTT)
        return rate if math.isfinite(rate) and rate > 0 else 0.0

    def w_cubic_packets(self, t: float) -> float:
        """W(t) in segments for the current epoch (see :func:`cubic_window`)."""
        return cubic_window(t, self._k, self._w_max / self._mss, self.config.c)

    def w_est_packets(self, t: float, rtt: float | None = None) -> float:
        """Reno-friendly estimate in segments: start + alpha * t / RTT."""
        rtt = self._srtt if rtt is None or not _valid_pos(rtt) else rtt
        alpha = reno_friendly_alpha(self.config.beta)
        return self._w_est_start + alpha * (t / max(rtt, _MIN_SRTT))

    # ------------------------------------------------------------------- events

    def on_packet_sent(self, pn: int, size: int, now: float) -> None:
        """Record the newest packet number (recovery boundary). Does NOT track bytes."""
        self._largest_sent_pn = max(self._largest_sent_pn, pn)

    def on_ack(
        self,
        acked_packets: Iterable[PacketLike],
        rtt_stats: RttLike | float | None,
        now: float,
    ) -> None:
        """Grow the window for newly acknowledged packets.

        ``acked_packets`` must contain only newly acked, congestion-controlled
        packets (ACK-only packets are not in flight and must be excluded).
        """
        self._update_srtt(rtt_stats)
        for pkt in acked_packets:
            size = pkt.size
            if not isinstance(size, (int, float)) or not size > 0:
                continue  # ignore bogus sizes instead of corrupting the window
            if pkt.pn <= self._recovery_pn:
                continue  # sent before the last loss: no growth, doesn't end recovery
            self._in_recovery = False
            self._collapsed = False
            if self._cwnd < self._ssthresh:
                self._slow_start(float(size), now)
            else:
                if self._epoch_start is None:
                    self._start_epoch(now)
                self._cubic_increase(float(size), now)
        self._sanitize()

    def on_loss(self, lost_packets: Iterable[PacketLike], now: float) -> None:
        """Fast-loss reaction (3 dup ACKs with SACK gaps, detected by reliability).

        One multiplicative decrease per recovery period; losses of packets sent
        before the current recovery period began are ignored.
        """
        if not any(p.pn > self._recovery_pn for p in lost_packets):
            return
        self._w_max = self._cwnd
        self._ssthresh = self._cwnd = self._reduced(self._cwnd)
        self._recovery_pn = self._largest_sent_pn
        self._in_recovery = True
        self._collapsed = False
        self._start_epoch(now, after_loss=True)
        self._sanitize()

    def on_timeout(self, now: float) -> None:
        """Retransmission timeout (mmt-ass1 "severe loss"): back to slow start.

        Interface addition: the design document only lists persistent
        congestion, but the assignment spec requires a distinct RTO reaction.
        Repeated timeouts without an intervening ACK do not overwrite
        ``W_max``/``ssthresh`` again.
        """
        if not self._collapsed:
            self._w_max = self._cwnd
            self._ssthresh = max(
                self._reduced(self._cwnd),
                float(self.config.min_cwnd_packets) * self._mss,
            )
        self._cwnd = float(self.config.timeout_cwnd_packets) * self._mss
        self._recovery_pn = self._largest_sent_pn
        self._in_recovery = False
        self._collapsed = True
        self._epoch_start = None
        self._sanitize()

    def on_persistent_congestion(self) -> None:
        """Persistent congestion (all packets over 3*PTO lost): cwnd = 2 * MSS.

        Returns to slow start. ``ssthresh`` is kept at least one MSS above the
        minimum window so there is room to slow-start (assumption, see docs).
        """
        min_cwnd = float(self.config.min_cwnd_packets) * self._mss
        if not self._collapsed:
            self._w_max = self._cwnd
            self._ssthresh = max(self._reduced(self._cwnd), min_cwnd + self._mss)
        self._cwnd = min_cwnd
        self._recovery_pn = self._largest_sent_pn
        self._in_recovery = False
        self._collapsed = True
        self._epoch_start = None
        self._sanitize()

    # ---------------------------------------------------------------- internals

    def _reduced(self, cwnd: float) -> float:
        """Multiplicative decrease with the minimum-window floor (bytes)."""
        mss, beta = self._mss, self.config.beta
        if self.config.floor_to_mss:
            reduced = math.floor(cwnd / mss * beta + _EPS) * mss
        else:
            reduced = cwnd * beta
        return max(reduced, float(self.config.min_cwnd_packets) * mss)

    def _slow_start(self, acked_bytes: float, now: float) -> None:
        self._cwnd += acked_bytes
        if self._cwnd >= self._ssthresh:
            self._cwnd = self._ssthresh  # land exactly on the threshold
            self._start_epoch(now)

    def _start_epoch(self, now: float, after_loss: bool = False) -> None:
        """Begin a cubic epoch at ``now``.

        With a known ``W_max`` the spec's ``K = cbrt(W_max(1-beta)/C)`` applies
        (the window starts near ``beta * W_max``). With no loss history
        (slow start reached ssthresh on its own) ``W_max = cwnd`` and ``K = 0``
        so growth begins in the convex probing region.
        """
        if self._w_max > 0:
            self._k = cubic_k(self._w_max / self._mss, self.config.beta, self.config.c)
        else:
            self._w_max = self._cwnd
            self._k = 0.0
        self._epoch_start = now
        self._w_est_start = self._cwnd / self._mss

    def _cubic_increase(self, acked_bytes: float, now: float) -> None:
        assert self._epoch_start is not None
        t = max(0.0, now - self._epoch_start)
        cwnd_pkts = self._cwnd / self._mss
        candidates = [self.w_cubic_packets(t), self.w_est_packets(t)]
        valid = [w for w in candidates if math.isfinite(w) and w > 0]
        if not valid:
            return
        target = min(max(valid), self.config.target_cap * cwnd_pkts)
        if target <= cwnd_pkts:
            return  # plateau around W_max: do not shrink, do not grow
        # (target - cwnd) / cwnd segments per segment acked => reach target in ~1 RTT
        grown = cwnd_pkts + (target - cwnd_pkts) / cwnd_pkts * (acked_bytes / self._mss)
        self._cwnd = min(grown, target) * self._mss

    def _update_srtt(self, rtt_stats: RttLike | float | None) -> None:
        value = getattr(rtt_stats, "smoothed_rtt", rtt_stats)
        if isinstance(value, (int, float)) and _valid_pos(value):
            self._srtt = max(float(value), _MIN_SRTT)
        # invalid / missing sample: keep the previous srtt (initially 333 ms)

    def _sanitize(self) -> None:
        """Keep cwnd finite, positive and below the sanity cap."""
        floor = float(self.config.timeout_cwnd_packets) * self._mss
        if not math.isfinite(self._cwnd) or self._cwnd < floor:
            self._cwnd = floor
        self._cwnd = min(self._cwnd, float(self.config.max_cwnd_bytes))


def _valid_pos(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0
