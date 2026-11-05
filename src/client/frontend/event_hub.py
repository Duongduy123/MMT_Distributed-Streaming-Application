"""Python -> browser event delivery. Status: SCAFFOLD; mechanism is decision D2.

Networking threads publish events (presence change, incoming message, delivery receipt, file
progress, connection status). The browser receives them through the local HTTP listener using
polling, long-polling or hand-written Server-Sent Events -- never WebSockets.

The buffer will be bounded (oldest events dropped with a counter) so a closed browser tab cannot
grow memory without limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UiEvent:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


class EventHub:
    """Thread-safe bounded event buffer between networking threads and the UI listener."""

    def publish(self, event: UiEvent) -> None:
        raise NotImplementedError("TODO(Phase 10, D2): bounded, thread-safe event buffer")

    def wait_events(self, after_id: int, timeout_s: float) -> list[tuple[int, UiEvent]]:
        raise NotImplementedError("TODO(Phase 10, D2): long-poll/SSE read side")
