"""Local API used by the browser JavaScript. Status: SCAFFOLD.

The browser never touches transport state directly. It calls ``/api/*`` on 127.0.0.1, and this
class turns each call into a command for the TCP control client or the UDP client (via the
transport scheduler). Endpoint paths/bodies are defined in Phase 10; none are registered yet,
so no fake responses exist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.client.frontend.event_hub import EventHub
from src.common.http.listener import Router

if TYPE_CHECKING:
    from src.client.tcp.tcp_client import TcpControlClient
    from src.client.udp.udp_client import UdpClient


class LocalApi:
    """Browser-facing command surface of the client process."""

    def __init__(self, tcp: TcpControlClient, udp: UdpClient, events: EventHub) -> None:
        self.tcp = tcp
        self.udp = udp
        self.events = events

    def register_routes(self, router: Router, prefix: str) -> None:
        """TODO(Phase 10): login, send chat (global/direct), file offer/accept, user list,
        status, and the event endpoint chosen in D2."""
        return None
