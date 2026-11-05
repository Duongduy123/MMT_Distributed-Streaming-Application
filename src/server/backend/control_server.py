"""Backend + TCP control plane listener (default 0.0.0.0:8080). Status: SCAFFOLD.

Decision D1 (provisional): exactly ONE listener on this port, speaking hand-written HTTP/1.1
over raw TCP. Backend APIs and control operations (handshake, login, session, presence, user
list, file metadata, UDP registration) are all HTTP endpoints routed by ``request_handler``.
No second listener and no binary protocol are ever bound to this address/port.
"""

from __future__ import annotations

from src.common.http.listener import RawHttpListener
from src.server.backend.authentication import Authenticator
from src.server.backend.presence_manager import PresenceManager
from src.server.backend.request_handler import ControlRequestHandler
from src.server.backend.session_manager import SessionManager


class ControlServer(RawHttpListener):
    """The single TCP 8080 listener."""

    def __init__(
        self,
        bind: str,
        port: int,
        auth: Authenticator,
        sessions: SessionManager,
        presence: PresenceManager,
    ) -> None:
        self.handler = ControlRequestHandler(auth, sessions, presence)
        super().__init__("control-plane", bind, port, self.handler.build_router())
