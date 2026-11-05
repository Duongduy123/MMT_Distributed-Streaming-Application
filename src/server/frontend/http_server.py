"""Server dashboard HTTP listener (default 127.0.0.1:3000). Status: SCAFFOLD.

Serves ``static/`` (index.html, css, js) and, in Phase 10, read-only monitoring endpoints
(service status, sessions, transport statistics) through the shared raw-socket HTTP layer.
Not exposed to the LAN unless ``--ui-bind 0.0.0.0`` is given (D12).
"""

from __future__ import annotations

from pathlib import Path

from src.common.http.listener import RawHttpListener, Router

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DashboardServer(RawHttpListener):
    """Dashboard listener. Routes are registered in Phase 10."""

    def __init__(self, bind: str, port: int) -> None:
        super().__init__("server-dashboard", bind, port, Router())
        self.static_dir = STATIC_DIR
