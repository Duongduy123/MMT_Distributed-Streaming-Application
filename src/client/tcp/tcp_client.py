"""TCP control client -> SERVER:8080. Status: SCAFFOLD.

Speaks the SAME hand-written HTTP/1.1 protocol as the backend (D1) through ``RawHttpClient``.
Responsibilities (Phases 3+): application handshake + ACK (rubric Step 2), login (Step 3),
session keep-alive, user list, presence events (D2), file offer/accept/done metadata, and UDP
endpoint registration.
"""

from __future__ import annotations

from src.client.frontend.event_hub import EventHub
from src.client.tcp.control_handler import ControlResponseHandler
from src.common.http.client import RawHttpClient


class TcpControlClient:
    """Implements ``lifecycle.Service``. Constructing it opens no connection."""

    def __init__(self, server_host: str, port: int, events: EventHub) -> None:
        self.name = "tcp-control-client"
        self.http = RawHttpClient(server_host, port)
        self.handler = ControlResponseHandler(events)

    def start(self) -> None:
        """Connect and perform the application-level handshake."""
        raise NotImplementedError(
            f"TODO(Phase 3, D1): control connection to {self.http.host}:{self.http.port}"
        )

    def stop(self) -> None:
        """Logout (best effort) and close. Idempotent."""
        self.http.close()
