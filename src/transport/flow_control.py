"""Flow control (receiver buffer protection). GATED ON D14 for sequence representation.

Responsibilities (architecture doc section 8, summary-sourced from flowcontrol-tcp.docx):
* sender window: SWS = min(rwnd, cwnd) with BOTH in the same unit (D6: bytes);
  LAR/LFS-equivalent bookkeeping;
* receiver window: LFR/LAF-equivalent, ring buffer (``MaxSlotBuff`` slots vs ``MaxByteBuff``
  bytes -- two different limits), advertised ``rwnd`` = free buffer actually released by the
  application (never widened merely because a frame arrived);
* zero window: persist timer + WND_PROBE with exponential backoff; probe replies are not RTT
  samples and do not count as duplicate ACKs;
* relay backpressure (D3): when the A->C leg cannot accept more, A shrinks the credit it
  advertises on the B->A leg; relay queues are bounded (limits = D12).
"""

from __future__ import annotations


class SenderFlowWindow:
    """Peer-advertised receive window as seen by the sender of one direction."""

    def update_peer_window(self, rwnd_bytes: int) -> None:
        raise NotImplementedError("TODO(Phase 6, D14): apply advertised rwnd")

    def allows(self, size: int, bytes_in_flight: int) -> bool:
        """Callback shape matches ``PacedSender(flow_allows=...)`` once adapted per packet."""
        raise NotImplementedError("TODO(Phase 6, D14): rwnd credit check")

    def on_probe_timer(self, now: float) -> None:
        raise NotImplementedError("TODO(Phase 6, D14): zero-window WND_PROBE with backoff")


class ReceiverFlowWindow:
    """Receive buffer + advertised window for one direction."""

    def advertised_window(self) -> int:
        raise NotImplementedError("TODO(Phase 6, D14): free bytes released by the application")

    def on_application_read(self, nbytes: int) -> None:
        raise NotImplementedError("TODO(Phase 6, D14): release buffer, slide window")
