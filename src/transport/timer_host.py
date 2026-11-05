"""Threading-based TimerHost (decision D11). Status: SCAFFOLD -- implemented in Phase 8.

Why: the existing ``PacedSender`` (copied unchanged) needs a timer host shaped like an event
loop (``time()`` + ``call_at()`` returning a cancellable handle). The team prohibits asyncio,
so this module provides the same three members on top of ``threading``.

Interface required by PacedSender (verified in paced_sender.py ``TimerHostLike`` and the
original tests' ``FakeLoop``):

=====================  =====================================================================
Member                 Contract this adapter must honor
=====================  =====================================================================
``time() -> float``    ``time.monotonic()``; the SAME clock is passed as ``now`` to Pacer
                       and CubicController.
``call_at(when, cb)``  Run ``cb`` on the scheduler thread at monotonic ``when``. If
                       ``when <= time()`` run it on the NEXT loop turn, never inline:
                       PacedSender yields with ``call_at(now)`` and inline execution would
                       recurse into ``_run``.
``handle.cancel()``    Idempotent; harmless after the callback ran.
=====================  =====================================================================

Planned implementation (Phase 8):

* ONE scheduler thread per process owns a heap of ``(when, seq, handle)`` protected by a
  ``threading.Condition``; it sleeps with ``cond.wait(timeout=when - now)`` -- no busy-wait.
* The lock is RELEASED before running a callback, so callbacks may call ``call_at``/``cancel``
  without deadlock. Cancelled handles are discarded lazily when popped.
* ``post(cb)`` = ``call_at(time(), cb)``: the only way other threads (UDP receive, HTTP, TCP)
  touch transport state. PacedSender, CubicController, Pacer, reliability and flow-control
  objects are therefore CONFINED to the scheduler thread; that is how the non-thread-safe
  PacedSender is used without modifying it.
* Callback exceptions are logged; they never kill the scheduler thread.
* ``stop()`` wakes the thread, drops pending timers and joins it. Idempotent.

Integration: ``PacedSender(..., loop=ThreadTimerHost(...), ...)`` -- structural typing, no
subclassing, no change to paced_sender.py.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class ThreadTimerHandle:
    """Cancellable handle returned by :meth:`ThreadTimerHost.call_at`."""

    __slots__ = ("when", "callback", "cancelled")

    def __init__(self, when: float, callback: Callable[[], Any]) -> None:
        self.when = when
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        """Mark as cancelled. Idempotent."""
        self.cancelled = True


class ThreadTimerHost:
    """Timer host backed by one scheduler thread. Implements ``lifecycle.Service``.

    Constructing it does NOT start a thread; :meth:`start` does (Phase 8).
    """

    def __init__(self, name: str = "transport-scheduler") -> None:
        self.name = name

    def time(self) -> float:
        """Monotonic seconds -- the single transport clock."""
        return time.monotonic()

    def call_at(self, when: float, callback: Callable[[], Any]) -> ThreadTimerHandle:
        """Schedule ``callback`` on the scheduler thread at monotonic ``when``."""
        raise NotImplementedError("TODO(Phase 8, D11): heap + Condition timer scheduling")

    def post(self, callback: Callable[[], Any]) -> ThreadTimerHandle:
        """Run ``callback`` on the scheduler thread as soon as possible (thread confinement)."""
        raise NotImplementedError("TODO(Phase 8, D11): cross-thread work submission")

    def start(self) -> None:
        """Start the scheduler thread."""
        raise NotImplementedError("TODO(Phase 8, D11): scheduler thread")

    def stop(self) -> None:
        """Stop and join the scheduler thread. Idempotent; safe if never started."""
        return None
