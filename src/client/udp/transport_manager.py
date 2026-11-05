"""Client-side glue to the shared ``src.transport`` package. Status: SCAFFOLD.

Holds the client's single ``TransportConnectionState`` (leg client<->A) and maps application
streams (chat = INTERACTIVE, file chunks = BULK) onto it. No algorithm lives here.
"""

from __future__ import annotations

from src.transport.connection_state import TransportConnectionState


class ClientTransportManager:
    """Bridges datagrams <-> the client's transport connection state."""

    def __init__(self) -> None:
        self.state: TransportConnectionState | None = None  # created after UDP registration

    def on_datagram(self, data: bytes) -> None:
        raise NotImplementedError("TODO(Phase 4, D14): decode + dispatch")

    def send_stream_data(self, payload: bytes, priority: int) -> None:
        raise NotImplementedError("TODO(Phase 8): enqueue + kick the paced sender")
