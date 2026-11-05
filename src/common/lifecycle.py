"""Service lifecycle: ordered start, reverse-order rollback on partial failure, idempotent stop.

Source: review item 8 ("partial startup failure and resource cleanup").
Status: IMPLEMENTED (orchestration only; concrete services are scaffold stubs).

Each long-running component (HTTP listener, control server, UDP server, scheduler) implements
:class:`Service`. ``start()`` is where sockets are created and threads launched -- never in
``__init__`` and never at import time.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from src.common.exceptions import ServiceStartError

log = logging.getLogger(__name__)


@runtime_checkable
class Service(Protocol):
    """A component with an explicit start/stop lifecycle."""

    name: str

    def start(self) -> None:
        """Acquire resources (bind sockets, start threads). Raise on failure."""
        ...

    def stop(self) -> None:
        """Release resources. Must be idempotent and safe if ``start`` failed half-way."""
        ...


class ServiceGroup:
    """Starts services in order; on failure stops already-started ones in reverse order.

    The service that *failed* is also asked to ``stop()`` so it can release anything it
    acquired before raising (e.g. a bound socket whose ``listen()`` failed).
    """

    def __init__(self, services: Sequence[Service]) -> None:
        self._services = list(services)
        self._started: list[Service] = []
        self._stopped = False

    @property
    def started(self) -> list[str]:
        """Names of services currently started, in start order."""
        return [s.name for s in self._started]

    def start_all(self) -> None:
        """Start every service. Raises :class:`ServiceStartError` after rolling back."""
        for service in self._services:
            try:
                log.info("starting service %s", service.name)
                service.start()
            except BaseException as exc:  # includes NotImplementedError and KeyboardInterrupt
                self._safe_stop(service)
                self._rollback()
                raise ServiceStartError(service.name, exc) from exc
            self._started.append(service)

    def stop_all(self) -> None:
        """Stop started services in reverse order. Idempotent."""
        if self._stopped:
            return
        self._stopped = True
        self._rollback()

    def _rollback(self) -> None:
        while self._started:
            self._safe_stop(self._started.pop())

    @staticmethod
    def _safe_stop(service: Service) -> None:
        try:
            log.info("stopping service %s", service.name)
            service.stop()
        except Exception:  # cleanup must continue for the remaining services
            log.exception("error while stopping service %s", service.name)
