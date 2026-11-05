# Protocol Overview (skeleton)

This document will become the "Protocol Specification" section of the submission report (PDF §10). It records only what has been agreed. Everything else is marked **TBD** with the decision that blocks it.

## 1. Layers

| Layer | Carried over | Defined in code | Status |
|---|---|---|---|
| Application messages (AUTH, MSG, FILE; GLOBAL/DIRECT scope) | Control plane and/or UDP streams | `src/common/protocol/application_messages.py` | Names only |
| Control operations (handshake, login, logout, session, user list, presence, UDP register, file offer/accept/reject/done) | HTTP/1.1 on TCP 8080 | `src/common/protocol/control_messages.py` | Names only; endpoints TBD (Phase 3) |
| Transport frames (DATA, ACK, WND_PROBE, RETX) | UDP 9000 | `src/common/protocol/transport_frames.py` | Names only; **gated on D14** |

These are three separate enums with no shared names. None of the values are wire codes.

## 2. Control plane: HTTP/1.1 on TCP 8080 (D1, provisional)

- Implemented by hand over raw TCP. There is one listener, and the Python client uses the same protocol.
- Bodies will be JSON. Requests use `Content-Length`; chunked request bodies are not accepted.
- **TBD (Phase 3):** endpoint paths and methods, request/response schemas, error codes, session-token transport, and the push mechanism (D2).
- **Rubric Step 2:** the application-level handshake request gets an explicit ACK response. This is in addition to the OS TCP three-way handshake.

## 3. Data plane: custom transport on UDP 9000

**Agreed so far:**

- Star topology with the server as relay.
- Hop-by-hop transport state, separate for each direction (D3).
- Selective retransmission only (no Go-Back-N).
- RTO in the style of RFC 6298: initial 1 s, minimum 200 ms, maximum 60 s, with exponential backoff.
- Fast retransmit after 3 duplicate ACKs that carry gap evidence.
- Zero-window probing.
- CRC32 per datagram.
- CUBIC congestion control and a token-bucket pacer.
- Priority order CONTROL > INTERACTIVE > BULK.

**TBD (D14):**

- the header layout;
- the sequence model (frame `seq` vs packet number + stream offset);
- the ACK format;
- endianness, timestamp unit and checksum coverage;
- MSS (the existing code uses 1200 B);
- the connection-ID field;
- the encryption envelope (D9).

## 4. Confirmations (D3)

| Signal | Layer | Meaning |
|---|---|---|
| Transport ACK | Transport, per hop | Only that the next hop received the data |
| Delivery receipt | Application, end to end | The recipient's client process received the message |
| `FILE_DONE` | Control, end to end | The recipient reassembled the file and the SHA-256 matched |

## 5. State diagrams and sequence diagrams

To be added once the endpoints (Phase 3) and D14 are fixed. These are rubric Step 1 deliverables and part of the report.
