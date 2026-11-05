"""UDP client socket -> SERVER:9000. Status: SCAFFOLD.

One ``socket(AF_INET, SOCK_DGRAM)`` with an OS-assigned ephemeral local port (it does NOT bind
local port 9000). The same socket sends to and receives from the server. A receive thread posts
datagrams to the scheduler thread (D11); sends go through the scheduler.
"""

from __future__ import annotations

from src.client.udp.transport_manager import ClientTransportManager


class UdpClient:
    """Implements ``lifecycle.Service``. Constructing it opens no socket."""

    def __init__(self, server_host: str, server_port: int) -> None:
        self.name = "udp-client"
        self.server = (server_host, server_port)
        self.transport = ClientTransportManager()

    def start(self) -> None:
        """Create the UDP socket and start the receive thread + scheduler."""
        raise NotImplementedError(
            f"TODO(Phase 4, D14): UDP client to {self.server[0]}:{self.server[1]}"
        )

    def stop(self) -> None:
        """Close socket, stop threads. Idempotent; safe if never started."""
        return None
