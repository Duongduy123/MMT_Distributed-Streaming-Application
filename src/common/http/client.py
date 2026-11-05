"""Raw-socket HTTP/1.1 client used by the client process's TCP control module.

Decision D1: the native Python TCP client talks to SERVER_IP:8080 using the SAME HTTP/1.1
protocol the backend serves -- there is no second TCP protocol on that port.

Status: SCAFFOLD -- implemented in Phase 3. Must handle partial reads/writes exactly like the
listener (see ``parser.py``) and apply connect/read timeouts. Never uses ``http.client``.
"""

from __future__ import annotations

from src.common.http.message import HttpResponse


class RawHttpClient:
    """Sends HTTP/1.1 requests over ``socket(AF_INET, SOCK_STREAM)``."""

    def __init__(self, host: str, port: int, timeout_s: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Perform one request/response exchange."""
        raise NotImplementedError("TODO(Phase 3, D1): raw-socket HTTP/1.1 client request")

    def close(self) -> None:
        """Close any open connection. Idempotent."""
        return None
