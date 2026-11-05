# Distributed Streaming-based Client-Server Collaboration Application

Computer Networks Assignment 1. The application provides real-time chat (global and direct), presence and reliable file transfer between machines on a LAN. Everything is built on **raw Python sockets** and a **custom transport over UDP**.

> **Current status: PROJECT SCAFFOLDING — VERIFIED.**
> The structure, configuration, interfaces, UI skeletons and tests are in place. **No network service works yet.** `python server.py` and `python client.py` validate their arguments, then exit with code **2** ("scaffold only — not implemented"). See [docs/CHECKPOINT.md](docs/CHECKPOINT.md).

## Architecture in one picture

Centralized client-server with distributed frontends. There are exactly **two process roles**.

```text
 Machine A — server.py (ONE process)               Machine B / C / … — client.py (ONE process each)
 ┌──────────────────────────────────────┐           ┌────────────────────────────────────────┐
 │ Dashboard   TCP 127.0.0.1:3000 (HTTP)│           │ Local UI + /api  TCP 127.0.0.1:3000    │◄─ browser
 │ Control     TCP 0.0.0.0:8080 (HTTP)  │◄── TCP ───│ TCP control client  → A:8080 (HTTP/1.1)│
 │ UDP server  UDP 0.0.0.0:9000 (relay) │◄── UDP ──►│ UDP client (ephemeral port) → A:9000   │
 └──────────────────────────────────────┘           └────────────────────────────────────────┘
       B and C never talk directly: A relays (B↔A and A↔C are separate transport connections)
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Open decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

## Ports and binds

| Service | Process | Protocol | Default bind | Port | Notes |
|---|---|---|---|---:|---|
| Server dashboard | server | TCP / HTTP/1.1 | `127.0.0.1` | 3000 | Local only; `--ui-bind 0.0.0.0` exposes it (needs a firewall rule) |
| Backend + control plane | server | TCP / HTTP/1.1 | `0.0.0.0` | 8080 | One listener (D1) |
| UDP transport + relay | server | UDP / custom | `0.0.0.0` | 9000 | Reliability, flow control, CUBIC, pacer |
| Client UI + local API | client | TCP / HTTP/1.1 | `127.0.0.1` | 3000 | Static files and `/api/*` on one listener |
| TCP control client | client | TCP | ephemeral | — | Connects to `SERVER:8080` |
| UDP client | client | UDP | ephemeral | — | Sends to `SERVER:9000`; does **not** bind local 9000 |

`0.0.0.0` is a *bind* address, never a destination. Clients must use A's real LAN IPv4. Find it with `python scripts/show_network_info.py`.

## Requirements and constraints

- Python **3.10+**, standard library only. No `pip install` is needed, and none is allowed without approval (see D9 on encryption).
- Raw `socket` only. Not allowed: Flask, Django, FastAPI, WebSockets, Socket.IO, `http.server`, `http.client`, `socketserver`, `asyncio`, `requests`, Scapy, aioquic, Twisted, and any reliability, congestion-control or pacing library. The full audit is in [docs/CONSTRAINT_AUDIT.md](docs/CONSTRAINT_AUDIT.md).
- Frontends use HTML, CSS and vanilla JavaScript only, with no build step and no Node.js.
- Concurrency uses `threading`, with explicit ownership (D11).

## Project tree

```text
server.py, client.py        the only two entry points
src/common/                 constants, config validation, lifecycle, exceptions, logging
src/common/http/            ONE hand-written HTTP/1.1 layer (listener, parser, client) — interfaces
src/common/protocol/        application / control / transport-frame names (separate enums); wire format gated on D14
src/transport/              SHARED transport: CUBIC, Pacer, PacedSender (existing, copied unchanged),
                            contracts, ThreadTimerHost, connection state, reliability/flow/scheduler stubs
src/server/                 application, dashboard (frontend/), control plane (backend/), UDP + relay (udp/)
src/client/                 application, local UI + API + event hub (frontend/), tcp/, udp/
tests/unit/                 config, contracts, isolation, import safety, scanner, lifecycle, transport/ (copied)
tests/integration/, manual/ plans only (nothing networked exists yet)
scripts/                    check_environment.py, constraint_scan.py, show_network_info.py
docs/                       architecture, plan, decisions, progress, checkpoint, audit, protocol, CC review
congestion_control/         ORIGINAL CUBIC/Pacer work, kept untouched (hash-verified)
```

## Commands that work today

Run all commands from the project root.

```powershell
python server.py --help
python client.py --help
python -m unittest discover -s tests -t . -v     # 135 tests
python scripts/check_environment.py               # Python version, files, stdlib-only, constraint scan
python scripts/constraint_scan.py                 # AST scan for prohibited imports
python scripts/show_network_info.py               # bind vs destination addresses of this machine
python server.py                                  # exits 2: "scaffold only — not implemented"
python client.py --server 127.0.0.1               # exits 2: "scaffold only — not implemented"
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | OK |
| 1 | Startup failure (already-started services are rolled back) |
| 2 | Service not implemented (scaffold) |
| 64 | Invalid arguments or configuration |

## Planned usage (does **not** work yet)

```powershell
# Machine A
python server.py                                  # dashboard at http://127.0.0.1:3000/ on A

# Machine B, C, … (use A's LAN IPv4)
python client.py --server 192.168.1.10            # then open http://127.0.0.1:3000/ on that machine

# One machine, several clients (each local UI needs its own port)
python server.py
python client.py --server 127.0.0.1 --ui-port 3001
python client.py --server 127.0.0.1 --ui-port 3002
```

On A, Windows Firewall must allow inbound **TCP 8080** and **UDP 9000**, and TCP 3000 too if the dashboard is exposed.

## Testing

- **Unit tests:** stdlib `unittest`, with no real sockets or threads: `python -m unittest discover -s tests -t . -v`.
- **Copied CUBIC/Pacer tests alone:** `python -m unittest discover -s tests/unit/transport -t . -v`.
- **Original CUBIC/Pacer tests:** `cd congestion_control` then `python -m unittest discover -s tests -t . -v`.
- **Integration and manual plans:** [tests/integration/README.md](tests/integration/README.md) and [tests/manual/README.md](tests/manual/README.md).

## Known limitations

- No HTTP listener, control protocol, UDP transport, relay, chat, file transfer, encryption or live UI exists yet. The UIs are clearly labeled placeholders.
- The CUBIC, Pacer and PacedSender code was implemented before this phase and copied unchanged. Its tests pass, but its **assignment compliance is UNVERIFIED** (D4, D5 and D14). See [docs/EXISTING_CC_REVIEW.md](docs/EXISTING_CC_REVIEW.md).
- The packet format is deliberately undefined until D14 (frame sequence vs packet number) is decided.
- Payload encryption (rubric Step 8) needs an approved dependency (D9).
- Three detailed design `.docx` files are now in the root but have not yet been reviewed against the decisions. Two are still missing (D10). See [docs/reference/README.md](docs/reference/README.md).
