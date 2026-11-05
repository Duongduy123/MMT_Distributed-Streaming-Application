"""Client UI listener (default 127.0.0.1:3000). Status: SCAFFOLD.

ONE listener serves both:
* static assets: ``/`` -> static/index.html, ``/css/*``, ``/js/*``
* local API:     ``/api/*`` -> :class:`LocalApi` (endpoint list defined in Phase 10)

Bound to loopback by default: the browser on the same machine is the only intended caller.
"""

from __future__ import annotations

from pathlib import Path

from src.client.frontend.local_api import LocalApi
from src.common.http.listener import RawHttpListener, Router

STATIC_DIR = Path(__file__).resolve().parent / "static"
API_PREFIX = "/api/"


class ClientUiServer(RawHttpListener):
    """Static files + local API on the same listener."""

    def __init__(self, bind: str, port: int, api: LocalApi) -> None:
        router = Router()
        api.register_routes(router, API_PREFIX)
        super().__init__("client-ui", bind, port, router)
        self.static_dir = STATIC_DIR
