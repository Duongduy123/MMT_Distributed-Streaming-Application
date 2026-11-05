"""Raw-socket HTTP/1.1 listener + router interface. Status: SCAFFOLD -- implemented in Phase 2.

One :class:`RawHttpListener` owns exactly one ``SOCK_STREAM`` listening socket. It is reused
by the server dashboard, the backend/control plane and the client local UI; each role only
registers different routes on its :class:`Router`.

Threading (D11): one accept thread per listener; each accepted connection is handled by a
worker thread from a bounded pool (never one thread per packet/byte). Long-lived responses
needed by D2 (long-poll or hand-written SSE) must not block the accept loop.

Send path: responses are written with a loop that handles partial ``send()`` results and a
per-connection timeout. ``Connection: close`` is the default.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.common.http.message import HttpRequest, HttpResponse

Handler = Callable[[HttpRequest], HttpResponse]


@dataclass(frozen=True)
class Route:
    """An exact (method, path) route. Prefix routes are used for static assets."""

    method: str
    path: str
    handler: Handler
    prefix: bool = False


class Router:
    """Maps (method, path) to a handler. Pure data structure: no sockets."""

    def __init__(self) -> None:
        self._routes: list[Route] = []

    def add(self, method: str, path: str, handler: Handler, prefix: bool = False) -> None:
        """Register a handler. Exact routes are matched before prefix routes."""
        self._routes.append(Route(method.upper(), path, handler, prefix))

    def resolve(self, method: str, path: str) -> Handler | None:
        """Return the handler for ``method``/``path`` or ``None`` (listener answers 404/405)."""
        method = method.upper()
        for route in self._routes:
            if not route.prefix and route.method == method and route.path == path:
                return route.handler
        best: Route | None = None
        for route in self._routes:
            if route.prefix and route.method == method and path.startswith(route.path):
                if best is None or len(route.path) > len(best.path):
                    best = route
        return best.handler if best else None


class RawHttpListener:
    """HTTP/1.1 server on one raw TCP socket. Implements ``lifecycle.Service``.

    The constructor stores configuration only; the socket is created in :meth:`start`.
    """

    def __init__(self, name: str, bind: str, port: int, router: Router) -> None:
        self.name = name
        self.bind = bind
        self.port = port
        self.router = router

    def start(self) -> None:
        """Create socket(AF_INET, SOCK_STREAM), bind, listen, start the accept thread."""
        raise NotImplementedError(
            f"TODO(Phase 2, D1): raw-socket HTTP listener for {self.name} "
            f"({self.bind}:{self.port}) not implemented"
        )

    def stop(self) -> None:
        """Close the listening socket and join worker threads. Idempotent; safe if not started."""
        # Nothing has been acquired in the scaffold, so there is nothing to release.
        return None
