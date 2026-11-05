"""Reliability over UDP. GATED ON D14 -- signatures use opaque types until the model is chosen.

Responsibilities (architecture doc section 7, summary-sourced from reliability-tcp.docx):
* sequence/packet-number management;
* ACK processing (cumulative + SACK under Model A, or ACK ranges under Model B);
* retransmission of ONLY missing data (selective repeat; never Go-Back-N);
* RTT sampling (Karn's rule under Model A; unambiguous under Model B) and RTO
  (RFC 6298 style: SRTT/RTTVAR, RTO = SRTT + 4*RTTVAR, initial 1 s, min 200 ms, max 60 s,
  exponential backoff);
* fast retransmit after 3 duplicate ACKs with SACK evidence;
* duplicate detection: duplicates are dropped but STILL acknowledged;
* corruption detection (CRC32) and end-to-end file integrity (SHA-256, application layer).

Reports to congestion control: ``on_ack`` / ``on_loss`` / ``on_timeout`` on the
``CongestionController`` of the same direction. Runs only on the scheduler thread (D11).
"""

from __future__ import annotations

from typing import Any

# Opaque placeholders until D14 fixes the frame/ACK structures.
OutboundUnit = Any
TransportFeedback = Any


class ReliabilitySender:
    """Sender half: tracks unacknowledged data and decides what to retransmit."""

    def on_send(self, unit: OutboundUnit, now: float) -> None:
        raise NotImplementedError("TODO(Phase 5, D14): record sent data for ACK/RTO tracking")

    def on_feedback(self, feedback: TransportFeedback, now: float) -> None:
        raise NotImplementedError("TODO(Phase 5, D14): ACK/SACK processing, RTT sample, loss")

    def on_rto_timer(self, now: float) -> None:
        raise NotImplementedError("TODO(Phase 5, D14): RTO expiry, backoff, retransmission")


class ReliabilityReceiver:
    """Receiver half: duplicate detection, reordering, ACK generation."""

    def on_data(self, unit: OutboundUnit, now: float) -> None:
        raise NotImplementedError("TODO(Phase 5, D14): accept/duplicate/out-of-window handling")

    def build_feedback(self, now: float) -> TransportFeedback:
        raise NotImplementedError("TODO(Phase 5, D14): build ACK (and SACK/ranges)")
