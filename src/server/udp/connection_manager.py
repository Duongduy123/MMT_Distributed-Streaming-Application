"""Transport connection table: connection id <-> session <-> UDP endpoint. Status: SCAFFOLD.

A datagram is attributed to a connection by its connection identifier AND the endpoint that was
registered through the authenticated control plane -- never by a username in the payload.
Idle/timeout detection feeds presence (connection resilience, rubric Step 7).
"""

from __future__ import annotations

from src.server.backend.session_manager import SessionManager
from src.transport.connection_state import TransportConnectionState


class ConnectionManager:
    """Thread-safe registry of server-side transport connections (one per client leg)."""

    def __init__(self, sessions: SessionManager) -> None:
        self.sessions = sessions

    def lookup(self, connection_id: int, endpoint: tuple[str, int]) -> TransportConnectionState | None:
        raise NotImplementedError("TODO(Phase 4, D14): connection lookup + endpoint check")

    def open(self, session_id: str, endpoint: tuple[str, int]) -> TransportConnectionState:
        raise NotImplementedError("TODO(Phase 4, D14): create per-leg transport state")

    def close(self, connection_id: int) -> None:
        raise NotImplementedError("TODO(Phase 4): tear down connection state")
