"""Control-plane operations carried over HTTP/1.1 on TCP 8080 (D1, provisional).

Source: architecture doc section 5.1 (connect, application handshake, authentication, session,
presence, user list, file control/metadata) and section 6.4 (file offer/accept/done flow).
Status: SCAFFOLD -- names only. HTTP methods, paths and JSON bodies are NOT defined yet; they are
specified in docs/PROTOCOL_OVERVIEW.md during Phase 3. Values are not wire codes.
"""

from __future__ import annotations

import enum


class ControlOperation(enum.Enum):
    """Logical control-plane operations (one or more HTTP endpoints each, TBD in Phase 3)."""

    HANDSHAKE = enum.auto()        # application-level connect + ACK (rubric Step 2)
    LOGIN = enum.auto()            # authentication (rubric Step 3)
    LOGOUT = enum.auto()
    SESSION_CHECK = enum.auto()    # validate / refresh a session
    USER_LIST = enum.auto()        # snapshot of online users
    PRESENCE_EVENTS = enum.auto()  # server -> client presence push; mechanism is D2
    UDP_REGISTER = enum.auto()     # bind authenticated session to its UDP endpoint (arch doc 12.1)
    FILE_OFFER = enum.auto()       # name, size, SHA-256, recipient
    FILE_ACCEPT = enum.auto()
    FILE_REJECT = enum.auto()
    FILE_DONE = enum.auto()        # end-to-end completion after SHA-256 verification (D3)
