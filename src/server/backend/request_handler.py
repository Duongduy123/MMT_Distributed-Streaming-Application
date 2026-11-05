"""Control-plane request routing (HTTP endpoints on 8080). Status: SCAFFOLD.

Maps ``ControlOperation`` values to HTTP endpoints. Paths, methods and JSON bodies are NOT
defined yet -- they are specified in docs/PROTOCOL_OVERVIEW.md during Phase 3. Until then the
router is empty and the listener would answer 404 for everything.
"""

from __future__ import annotations

from src.common.http.listener import Router
from src.server.backend.authentication import Authenticator
from src.server.backend.presence_manager import PresenceManager
from src.server.backend.session_manager import SessionManager


class ControlRequestHandler:
    """Translates HTTP requests into calls on auth/session/presence managers."""

    def __init__(
        self, auth: Authenticator, sessions: SessionManager, presence: PresenceManager
    ) -> None:
        self.auth = auth
        self.sessions = sessions
        self.presence = presence

    def build_router(self) -> Router:
        """Return the control-plane router. TODO(Phase 3, D1): register endpoints."""
        return Router()
