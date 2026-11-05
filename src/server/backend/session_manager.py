"""Sessions and session <-> UDP endpoint binding. Status: SCAFFOLD.

Tracks, per authenticated user (rubric Step 3): session id/token, TCP peer IP and port, and the
UDP endpoint + transport connection id registered for that session (architecture doc 12.1).
Identity is the authenticated session -- never a self-declared username or a bare IP:port.

Thread safety: accessed by control-plane worker threads and the UDP receive thread; every public
method will take an internal ``threading.Lock`` (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    username: str
    tcp_peer: tuple[str, int]
    udp_endpoint: tuple[str, int] | None = None
    connection_id: int | None = None


class SessionManager:
    """Creates, validates, revokes sessions; maps sessions to UDP connections."""

    def create(self, username: str, tcp_peer: tuple[str, int]) -> SessionInfo:
        raise NotImplementedError("TODO(Phase 3): session creation")

    def validate(self, session_id: str) -> SessionInfo | None:
        raise NotImplementedError("TODO(Phase 3): session validation")

    def revoke(self, session_id: str) -> None:
        raise NotImplementedError("TODO(Phase 3): session revocation")

    def bind_udp(self, session_id: str, endpoint: tuple[str, int], connection_id: int) -> None:
        raise NotImplementedError("TODO(Phase 4, D14): authenticated UDP registration")
