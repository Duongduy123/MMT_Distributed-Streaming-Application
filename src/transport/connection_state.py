"""Per-connection, per-direction transport state. Status: SCAFFOLD.

Relay model (D3): the server terminates every leg. For clients B and C relaying via A there are
two transport connections, B<->A and A<->C, and each has two directions:

    client B: conn(B<->A)  send B->A, receive A->B
    server A: conn(A<->B)  send A->B, receive B->A
              conn(A<->C)  send A->C, receive C->A
    client C: conn(C<->A)  send C->A, receive A->C

Every direction owns its OWN reliability buffers, RTT/RTO, flow-control window, congestion
controller, pacer and send queue. No two instances may share a mutable object (enforced by
tests/unit/test_connection_state.py).

Ownership (D11): mutated only on the process's scheduler thread (see ``timer_host``).
Sequence-number representation is GATED ON D14, so reliability/flow fields are opaque here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.transport.congestion_control import CubicController
from src.transport.pacer import Pacer
from src.transport.paced_sender import PriorityPacketQueue


@dataclass
class SendDirectionState:
    """Everything the sending side of one direction needs."""

    congestion: CubicController = field(default_factory=CubicController)
    queue: PriorityPacketQueue = field(default_factory=PriorityPacketQueue)
    pacer: Pacer | None = None  # created at connection start: Pacer needs a ``now`` value
    bytes_in_flight: int = 0    # D6: bytes
    reliability: object | None = None  # GATED ON D14: sent buffer, RTO/RTT, retransmission
    flow: object | None = None         # GATED ON D14: peer rwnd, LAR/LFS-equivalent, probe timer


@dataclass
class ReceiveDirectionState:
    """Everything the receiving side of one direction needs."""

    reliability: object | None = None  # GATED ON D14: received ranges, duplicate detection
    flow: object | None = None         # GATED ON D14: reorder/ring buffer, advertised rwnd


@dataclass
class TransportConnectionState:
    """One transport connection (one leg of the star) with both directions."""

    connection_id: int
    peer_label: str  # human-readable, e.g. "A<->B"; NOT an identity (identity = session, D3)
    send: SendDirectionState = field(default_factory=SendDirectionState)
    receive: ReceiveDirectionState = field(default_factory=ReceiveDirectionState)
