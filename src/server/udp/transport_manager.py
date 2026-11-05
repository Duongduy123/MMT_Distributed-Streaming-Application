"""Server-side glue between the UDP socket and the shared ``src.transport`` package.

Status: SCAFFOLD. Creates one ``TransportConnectionState`` per client leg (A<->B, A<->C, ...),
registers it with the process ``TransportScheduler`` and dispatches received datagrams to the
right state. Contains NO reliability/flow/congestion algorithm of its own.
"""

from __future__ import annotations

from src.server.udp.connection_manager import ConnectionManager


class ServerTransportManager:
    """Bridges datagrams <-> per-connection transport state on the server."""

    def __init__(self, connections: ConnectionManager) -> None:
        self.connections = connections

    def on_datagram(self, data: bytes, endpoint: tuple[str, int]) -> None:
        raise NotImplementedError("TODO(Phase 4, D14): decode + dispatch to connection state")

    def send_stream_data(self, connection_id: int, payload: bytes, priority: int) -> None:
        raise NotImplementedError("TODO(Phase 8): enqueue on the leg's send queue + kick")
