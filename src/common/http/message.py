"""HTTP/1.1 request/response value objects. Status: SCAFFOLD (data containers only)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HttpRequest:
    """A fully received request (headers parsed, body read according to Content-Length).

    Header names are stored lower-cased; values are kept as received (whitespace-trimmed).
    """

    method: str
    target: str
    version: str = "HTTP/1.1"
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass
class HttpResponse:
    """A response to be serialized by the listener's send loop."""

    status: int
    reason: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
