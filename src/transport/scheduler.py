"""Process-wide send scheduler. Status: SCAFFOLD -- implemented in Phase 8.

One scheduler per process (server or client). It owns the :class:`ThreadTimerHost` (D11) and one
``PacedSender`` per connection direction. Eligibility for every packet (no bypass allowed):

1. flow-control credit (rwnd),
2. ``bytes_in_flight + size <= cwnd`` (ACK-only packets exempt),
3. pacer tokens (ACK-only packets exempt),
4. priority: CONTROL > INTERACTIVE (chat) > BULK (file chunks), FIFO within a class,

then the datagram is written to the OWNING UDP socket (server: UDP 9000 socket; client: its
ephemeral-port socket). No busy-waiting: blocked senders are woken by ``kick()`` (ACK, credit,
enqueue) or by a single pacing timer.
"""

from __future__ import annotations

from collections.abc import Callable

from src.transport.connection_state import TransportConnectionState
from src.transport.timer_host import ThreadTimerHost

DatagramSender = Callable[[bytes, tuple[str, int]], None]


class TransportScheduler:
    """Owns the scheduler thread and the per-direction send gates. Implements ``Service``."""

    def __init__(self, timer_host: ThreadTimerHost, send_datagram: DatagramSender) -> None:
        self.name = "transport-scheduler"
        self._timer_host = timer_host
        self._send_datagram = send_datagram

    def register(self, state: TransportConnectionState, peer: tuple[str, int]) -> None:
        """Create the PacedSender for ``state.send`` bound to ``peer``."""
        raise NotImplementedError("TODO(Phase 8): wire PacedSender + flow/cc/pacer per direction")

    def unregister(self, connection_id: int) -> None:
        raise NotImplementedError("TODO(Phase 8): close PacedSender, cancel timers")

    def start(self) -> None:
        raise NotImplementedError("TODO(Phase 8, D11): start timer host / scheduler thread")

    def stop(self) -> None:
        """Idempotent; safe if never started."""
        return None
