"""Online/offline presence and user-list synchronization. Status: SCAFFOLD.

"Broadcast presence" is application-level fan-out to logged-in clients, not UDP broadcast
(architecture doc 5.2). The delivery mechanism to clients is D2 (polling / long-poll / SSE).
"""

from __future__ import annotations


class PresenceManager:
    """Tracks who is online and publishes presence changes."""

    def set_online(self, username: str) -> None:
        raise NotImplementedError("TODO(Phase 3, D2): presence online + event publication")

    def set_offline(self, username: str) -> None:
        raise NotImplementedError("TODO(Phase 3, D2): presence offline (logout/timeout)")

    def online_users(self) -> list[str]:
        raise NotImplementedError("TODO(Phase 3): user list snapshot")
