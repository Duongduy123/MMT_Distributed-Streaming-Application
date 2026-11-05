"""Interprets control-plane responses/events and forwards them to the UI. Status: SCAFFOLD."""

from __future__ import annotations

from src.client.frontend.event_hub import EventHub
from src.common.http.message import HttpResponse


class ControlResponseHandler:
    """Turns control-plane HTTP responses into local state updates and UI events."""

    def __init__(self, events: EventHub) -> None:
        self.events = events

    def handle(self, response: HttpResponse) -> None:
        raise NotImplementedError("TODO(Phase 3): map control responses to UI events")
