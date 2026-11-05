# Constraint Audit

- **Audit date:** 2026-11-05.
- **Phase:** project scaffolding.
- **Environment:** Python 3.12.10, Windows 11.
- **Status values:**

  | Status | Meaning |
  |---|---|
  | **PASS** | Verified by the command shown in the Evidence column |
  | **FAIL** | Violated |
  | **UNVERIFIED** | Cannot be verified yet (the feature doesn't exist) |
  | **CONFLICT** | Sources disagree; see the decision |

## 1. How the audit is done

1. **AST scanner:** `python scripts/constraint_scan.py`. It scans `server.py`, `client.py`, `src/`, `tests/` and `scripts/` for:
   - plain imports (`import x`, `import x as y`);
   - from-imports, including submodule forms such as `from http import server`;
   - `__import__` and `importlib.import_module` with literal arguments;
   - non-literal dynamic imports, reported as UNVERIFIABLE;
   - `exec`/`eval` of source text containing "import", reported as REVIEW.

   Prohibited names inside strings, comments or docstrings are not imports and are not reported. The scanner checks itself in `tests/unit/test_constraint_scanner.py`.
2. **Manual grep (cross-check):** a word-boundary grep for every prohibited name across `*.py`. Each hit is reviewed by hand below.
3. **Structural tests:**
   - import safety (patched `socket.socket` and `Thread.start`);
   - exactly two `__main__` entry points;
   - no transport classes under `src/server` or `src/client`;
   - default binds;
   - per-connection state isolation.
4. **Hash checks** of the original CUBIC/Pacer code (`EXISTING_CC_REVIEW.md`).

## 2. Results

| # | Requirement | Source | Status | Evidence | Corrective action |
|---|---|---|---|---|---|
| 1 | No HTTP frameworks (Flask, Django, FastAPI, Starlette, Tornado, aiohttp) | PDF §8 | PASS | AST scan: PROHIBITED=0 over 77 files | — |
| 2 | No WebSockets / Socket.IO | PDF §8 | PASS | AST scan. Grep of the frontend JS for `WebSocket`, `fetch(`, `XMLHttpRequest` and `EventSource` matches only the "no WebSockets" header comments | — |
| 3 | No `http.server`, `http.client`, `socketserver`, `urllib.request`, `requests` | Team rule (brief §3.2) | PASS | AST scan. Grep hits are only docstrings in `src/common/http/*.py` and the module name `src.common.http.client` | — |
| 4 | No `asyncio` | Team rule (D11) | PASS | AST scan. Grep hits are only comments/docstrings in `paced_sender.py` (copied) and `timer_host.py` | — |
| 5 | No Scapy, aioquic, Twisted, gevent, eventlet | Brief §3.2 | PASS | AST scan | — |
| 6 | No library providing reliability, CUBIC, sliding window or pacing | Brief §3.2 | PASS | The only imports are stdlib (see row 8); transport code is the project's own | — |
| 7 | Raw sockets for networking | PDF §8 | PASS (interfaces) / UNVERIFIED (implementation) | The only network API imported is `socket` (in `scripts/show_network_info.py`); listeners are stubs | Re-audit at Phases 2–4 |
| 8 | No third-party dependency | Brief §3.2 | PASS | `check_environment.py`: no dependency manifests. Unique imports: `__future__ argparse ast collections dataclasses enum ipaddress logging math pathlib platform socket sys threading time typing`, plus in tests: `unittest`, `importlib`, `pkgutil`, `contextlib`, `io`, `heapq`, `itertools` (the last two come from the copied CUBIC tests) | `ipaddress`, `platform`, `ast`, `pkgutil` and `contextlib` are not on the brief's "permitted" list. They are plain utilities with no networking; listed here for transparency |
| 9 | Exactly two process roles | Brief §2, ARCH §2 | PASS | `test_exactly_two_entry_points`; no `multiprocessing`/`subprocess` (AST scan) | — |
| 10 | No listener or thread on import | Brief §4.2 | PASS | `test_import_safety` imports every `src` module and builds both applications with sockets and threads forbidden | — |
| 11 | Ports 3000 / 8080 / 9000 defined in one place | Brief §5.1 | PASS | Grep: numeric literals occur only in `constants.py`; other hits are docstrings/help text | — |
| 12 | Separate network bind and dashboard bind; dashboard not on the LAN by default | Review item 4, D12 | PASS | `test_defaults`, `test_default_constants_are_separate` | — |
| 13 | Client UI on loopback by default | Brief §2.2 | PASS | `ClientConfigTests.test_valid` | — |
| 14 | `0.0.0.0` rejected as a client destination; port/IP validation; TCP collision check | Review item 8 | PASS | `test_configuration.py` and CLI runs (exit 64) | — |
| 15 | Transport algorithms shared, not duplicated in server/client | Brief §4.1 | PASS | `test_transport_algorithms_not_duplicated_in_server_or_client` | — |
| 16 | Independent state per connection and direction | Brief §4.1, D3 | PASS (container) / UNVERIFIED (algorithms) | `test_connection_state.py` | Extend when reliability/flow state exists |
| 17 | Frontends: HTML/CSS/vanilla JS, no framework, no build step | Brief §3.3 | PASS | Six static files; no `<script src>` other than the local `/js/app.js`; no `package.json` | — |
| 18 | Two different UIs | Brief §6 | PASS | Dashboard = monitoring tables; client = login, users, chat, files | — |
| 19 | No fake functionality | Brief §10 | PASS | Stubs raise `NotImplementedError`; `run()` exits 2 with "scaffold only"; the JS makes no requests | — |
| 20 | Existing CUBIC/Pacer copied unchanged | Review item 7 | PASS | SHA-256 identical; originals re-hashed unchanged | — |
| 21 | Existing CUBIC/Pacer meets the team spec | ARCH §9–10 | CONFLICT / UNVERIFIED | `EXISTING_CC_REVIEW.md` §4 | Resolve D4, D5, D14 |
| 22 | Concurrency (multi-threading or async I/O) | PDF §6, rubric S4 | UNVERIFIED | Design in D11; not implemented | Phase 2 and 8 |
| 23 | Payload encryption with a standard cryptographic library | PDF rubric S8 | UNVERIFIED / OPEN | D9: no AES in stdlib | Team/instructor decision |
| 24 | TCP vs UDP roles as worded in the PDF | PDF §3, §6, S2, S6 | CONFLICT | D8 | Ask the instructor |
| 25 | Runs on Windows/macOS/Linux with localhost or LAN IP | PDF §8 | UNVERIFIED | Verified on Windows only, and only CLI/tests | Test on a second OS in Phase 12 |
| 26 | Server handles 10–20 concurrent clients | PDF §7 | UNVERIFIED | — | Phase 12 |

## 3. REVIEW-tier findings (accepted)

| Finding | Why accepted |
|---|---|
| `tests/unit/test_import_safety.py:5 import importlib` | Test-only. It imports every package module to prove that importing has no side effects |
| `tests/unit/test_import_safety.py:43 import_module(<expr>)` marked ALLOWED by pragma | Same as above. The module names come from `pkgutil.walk_packages(src.__path__)` |

## 4. Not covered by the automated scan

- The `congestion_control/` originals. They were checked by grep: they import only `math`, `dataclasses`, `typing`, `collections`, `enum` and `heapq`, and there is no asyncio import.
- The JavaScript files, which were reviewed by hand.
