# Integration tests

None exist yet. Nothing that crosses a real socket has been implemented.

Planned, in the order the phases land (see `docs/PROJECT_PLAN.md`):

| Phase | Test | Uses |
|---|---|---|
| 2 | HTTP listener handles a request split across many `recv()` calls, and a large response written with partial `send()` calls | loopback TCP |
| 3 | Handshake → login → user list → logout; a second client sees the presence change | loopback TCP |
| 4–6 | Transport over a lossy/reordering/duplicating UDP shim, including the zero-window probe | loopback UDP |
| 7–8 | Pacing keeps bursts ≤ bucket; CONTROL/INTERACTIVE goes ahead of BULK | `ThreadTimerHost` |
| 9 | Direct + global relay with ≥ 2 clients; a slow client does not block the others | loopback TCP+UDP |
| 12 | 10–20 concurrent clients; abrupt disconnects; server keeps running | loopback / LAN |

Rules:

- Bind only to `127.0.0.1` with port `0` (OS-assigned), so tests never collide with a running server.
- Always close sockets and join threads in `tearDown`.
- Never assert on timing alone.
