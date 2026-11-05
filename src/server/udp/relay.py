"""Application routing/relay between clients (rubric Step 5). Status: SCAFFOLD.

Two-hop model (D3): data from B arrives on leg B->A and is re-sent on leg A->C (direct) or on
every other online leg (global fan-out). Hop-by-hop ACKs on B->A prove only that A received it.
End-to-end delivery receipts and FILE_DONE (after SHA-256 verification at C) are separate
application messages relayed back to B.

Backpressure: relay queues are bounded per destination (limits = D12). A slow client must not
block delivery to other clients; if A->C is blocked, A reduces credit on B->A.
"""

from __future__ import annotations

from src.server.udp.connection_manager import ConnectionManager
from src.server.udp.transport_manager import ServerTransportManager


class Relay:
    """Routes application payloads from one client leg to one or many other legs."""

    def __init__(self, connections: ConnectionManager, transport: ServerTransportManager) -> None:
        self.connections = connections
        self.transport = transport

    def forward_direct(self, from_session: str, to_user: str, payload: bytes) -> None:
        raise NotImplementedError("TODO(Phase 9, D3): unicast relay")

    def broadcast(self, from_session: str, payload: bytes) -> None:
        raise NotImplementedError("TODO(Phase 9, D3): global fan-out with per-destination bounds")
