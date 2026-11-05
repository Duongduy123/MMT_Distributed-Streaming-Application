"""Incremental HTTP/1.1 parser interface. Status: SCAFFOLD -- implemented in Phase 2.

Requirements the implementation MUST meet (review item 8):

* **Partial reads.** TCP is a byte stream: one ``recv()`` may return part of a request line,
  several headers, or bytes belonging to the body. ``feed()`` accumulates bytes until the
  ``\\r\\n\\r\\n`` header terminator is seen; it never assumes one ``recv()`` == one request.
* **Header cap.** Reject (431) when headers exceed ``max_header_bytes`` before the terminator.
* **Body by Content-Length only.** Chunked *request* bodies are rejected (400/411); body size is
  capped by ``max_body_bytes`` (413).
* **Malformed input** -> :class:`~src.common.exceptions.ProtocolError` mapped to 400; the parser
  never raises arbitrary exceptions into the listener's accept loop.
* **Partial writes** are the listener's responsibility (see ``listener.py``): ``socket.send``
  may write fewer bytes than given, so the send loop must continue until all bytes are written
  or the per-connection timeout expires.
"""

from __future__ import annotations

from src.common.http.message import HttpRequest

DEFAULT_MAX_HEADER_BYTES = 16 * 1024
DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024  # control/API bodies only; file bytes go over UDP


class HttpRequestParser:
    """Feeds raw bytes from one TCP connection; yields complete requests."""

    def __init__(
        self,
        max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        self.max_header_bytes = max_header_bytes
        self.max_body_bytes = max_body_bytes

    def feed(self, data: bytes) -> list[HttpRequest]:
        """Consume ``data`` (any size, possibly a fragment) and return completed requests."""
        raise NotImplementedError("TODO(Phase 2, D1): incremental HTTP/1.1 request parsing")

    def eof(self) -> None:
        """Signal peer close; raise ProtocolError if a request was left incomplete."""
        raise NotImplementedError("TODO(Phase 2, D1): EOF handling for partial requests")
