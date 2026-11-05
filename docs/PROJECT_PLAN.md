# Project Plan

**Deadline:** Sunday 17 Nov 2026, 23:59 (PDF §10).

**Rubric mapping:** S1–S10 are the PDF §9 rubric steps.

**Rule:** a phase is done only when its acceptance criteria have been **run** and the results are recorded in `PROGRESS.md`.

| # | Phase | Depends on | Rubric | Acceptance criteria |
|---|---|---|---|---|
| 1 | **Project scaffolding** ✅ | — | S1 (partial), S10 | Structure, config validation, interfaces, UI skeletons, docs; `unittest` green; constraint scan PASS; originals untouched |
| 2 | Protocol and socket foundation | 1, D1, D11 | S2, S4, S7 | `RawHttpListener` + parser + send loop; `ThreadTimerHost`; integration test with requests split across `recv()` calls and partial `send()`; clean shutdown |
| 3 | TCP control plane | 2, D2 | S2, S3, S4 | Endpoints specified in `PROTOCOL_OVERVIEW.md`; handshake + ACK; login; server tracks user IP and ports; presence/user list; 2+ concurrent clients |
| 4 | UDP packet protocol | **D14**, D6, D9 (envelope room) | S1, S6 | Header spec + codec; round-trip and CRC tests; session ↔ UDP endpoint registration |
| 5 | Reliability | 4 | S6 | ACK/SACK or ACK ranges, selective retransmit, RTO (RFC 6298), fast retransmit, duplicate handling; tests with a lossy/reordering shim |
| 6 | Flow control | 4, 5 | S6 | rwnd in bytes, receive buffer, zero-window probe with backoff; relay backpressure |
| 7 | CUBIC | D4, D5, D14 | — | Resolve the existing-code differences (`EXISTING_CC_REVIEW.md`); integrate with reliability events |
| 8 | Pacer and scheduler | 2, 5–7, D12 | S5 | `TransportScheduler` + `PacedSender` on `ThreadTimerHost`; bounded queues; CONTROL > INTERACTIVE > BULK |
| 9 | Relay and application routing | 3, 8, D3 | S5, S6 | Direct + global chat; file chunking/reassembly with SHA-256 and `FILE_DONE`; a slow client does not block others |
| 10 | Frontend integration | 3, 9, D2 | S9 | Local API + events; message list, user list, progress bars; dashboard live data |
| 11 | Security and resilience | D9 | S7, S8 | Payload encryption; timeouts, broken pipes and abrupt exits never crash the server |
| 12 | Integration testing and final validation | all | S10 | 10–20 concurrent clients; multi-terminal and LAN runs; report (architecture, protocol spec, sequence diagrams, challenges) |

## Critical path
D14 → Phase 4 → 5 → 6 → 8 → 9 → 10.

Resolve **D14** first. Phases 2–3 can proceed in parallel, because they depend only on D1 and D2.

## Phase 2: suggested first tasks
1. `HttpRequestParser.feed()`, with tests for byte-by-byte feeding, header and body caps, and malformed input.
2. `RawHttpListener.start()/stop()`: a bounded worker pool, a send loop that handles partial writes, and timeouts.
3. Static-file serving for both UIs (path normalization, so `..` cannot escape the static folder).
4. `ThreadTimerHost`, tested with the **unchanged** `PacedSender` on a real thread.
