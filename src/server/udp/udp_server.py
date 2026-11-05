"""UDP transport server socket owner (default 0.0.0.0:9000). Status: SCAFFOLD.

Owns the ONE server ``socket(AF_INET, SOCK_DGRAM)``. A receive thread reads datagrams and posts
them to the transport scheduler thread (D11); all sends go through the scheduler, which writes
to this socket. Low-level parsing never performs application routing (that is ``relay``).
"""

from __future__ import annotations

from src.server.backend.session_manager import SessionManager
from src.server.udp.connection_manager import ConnectionManager
from src.server.udp.relay import Relay
from src.server.udp.transport_manager import ServerTransportManager


class UdpTransportServer:
    """Implements ``lifecycle.Service``. Constructing it opens no socket."""

    def __init__(self, bind: str, port: int, sessions: SessionManager) -> None:
        self.name = "udp-transport"
        self.bind = bind
        self.port = port
        self.connections = ConnectionManager(sessions)
        self.transport = ServerTransportManager(self.connections)
        self.relay = Relay(self.connections, self.transport)

    def start(self) -> None:
        """Create/bind the UDP socket, start the receive thread and the scheduler."""
        raise NotImplementedError(
            f"TODO(Phase 4, D14): UDP server on {self.bind}:{self.port} not implemented"
        )

    def stop(self) -> None:
        """Close the socket, stop threads. Idempotent; safe if never started."""
        return None
