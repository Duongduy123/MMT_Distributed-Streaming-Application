# Progress Log

## 2026-11-05: Phase 1, project scaffolding

**Result: PROJECT SCAFFOLDING — VERIFIED.** The network application itself is **not** implemented.

### Inspection
- `ass1/` was **not** a git repository. Python is 3.12.10 on Windows 11.
- Pre-existing files were preserved:
  - the assignment PDF;
  - `MMT_Assignment_Architecture_and_Transport_Design.md`;
  - `congestion_control/` (10 files);
  - `lovvit_cc_cubic_pacer.zip`, byte-identical to `congestion_control/` after CRLF normalization.
- At inspection, the five design `.docx` files were not in the workspace (D10).
- During the session, `congestioncontrol.docx`, `flowcontrol-tcp.docx` and `reliability-tcp.docx` appeared in the root (mtime 2026-11-04 15:27–15:31). They have **not** been read yet. `Assign1-Design (1).docx` and `Thiết-kế-…(2).docx` are still missing.
- The plan was reviewed once (v1 → v2, review items 1–10) and then approved.

### Work done
| Area | Files | Status |
|---|---|---|
| Entry points | `server.py`, `client.py` | Parse → validate → run; honest exit 2; exit 64 on bad config |
| Common | `src/common/{constants,config,exceptions,logging_config,lifecycle}.py` | Implemented: config validation, ordered start with reverse rollback |
| Shared HTTP layer | `src/common/http/{message,parser,listener,client}.py` | `Router` implemented; listener, parser and client are stubs (D1) |
| Protocol | `src/common/protocol/*` | Three separate names-only enums; header/codec gated on D14 |
| Transport | `src/transport/*` | CUBIC, Pacer and PacedSender **copied unchanged**; contracts; `ThreadTimerHost` skeleton; connection-state container; reliability/flow/scheduler stubs |
| Server | `src/server/**` (16 files + 3 static) | Interface stubs; dashboard skeleton |
| Client | `src/client/**` (14 files + 3 static) | Interface stubs; client UI skeleton |
| Tests | `tests/unit/*` (6 new files + 4 copied), `tests/integration/README.md`, `tests/manual/README.md` | 135 tests |
| Scripts | `scripts/{constraint_scan,check_environment,show_network_info}.py` | Implemented |
| Docs | `README.md`; `docs/{ARCHITECTURE,PROJECT_PLAN,DECISIONS,PROGRESS,CHECKPOINT,CONSTRAINT_AUDIT,PROTOCOL_OVERVIEW,EXISTING_CC_REVIEW}.md`; `docs/reference/README.md`; `.gitignore` | Written |

### Commands run and actual results
| # | Command (from `ass1/` unless noted) | Result |
|---|---|---|
| 1 | SHA-256 of 10 originals + zip | Recorded in `EXISTING_CC_REVIEW.md` §1 |
| 2 | `cd congestion_control && python -m unittest discover -s tests -t .` (baseline) | `Ran 92 tests … OK` |
| 3 | `cp` 3 implementation files + 4 test files | Done |
| 4 | SHA-256 copies vs originals | 3 implementation files and `fakes.py` IDENTICAL |
| 5 | `sed` import rewrite + difflib check | 6 / 2 / 8 changed lines, all IMPORT-ONLY |
| 6a | `python -m unittest discover -s tests/unit/transport -t .` | `Ran 92 tests … OK` |
| 6b | Original suite again | `Ran 92 tests … OK` |
| 6c | `python -m unittest discover -s tests -t .` | `Ran 135 tests … OK` (0 failures, 0 errors) |
| 7 | Re-hash originals | All 11 unchanged. Test-generated `__pycache__/` in `congestion_control/` removed |
| 8 | `python server.py --help`, `python client.py --help` | Usage printed, exit 0 |
| 9 | `python client.py --server 0.0.0.0` | `error: --server: 0.0.0.0 is a wildcard bind address, not a destination…`, exit 64 |
| 10 | `python client.py --server 999.1.1.1` | `error: --server: '999.1.1.1' is not a valid IPv4 address`, exit 64 |
| 11 | `python client.py --server 192.168.1.10 --tcp-port 70000` | `error: --tcp-port: port 70000 outside 1..65535`, exit 64 |
| 12 | `python server.py --ui-port 8080 --ui-bind 0.0.0.0` | `error: TCP port collision: dashboard 0.0.0.0:8080 overlaps control listener 0.0.0.0:8080…`, exit 64 |
| 13 | `python server.py` | Logs "scaffold only -- service 'control-plane' is not implemented yet … No listener is running.", exit 2, returns immediately |
| 14 | `python client.py --server 127.0.0.1` | Logs "scaffold only -- service 'udp-client' …", exit 2 |
| 15 | `python scripts/constraint_scan.py` | 77 files; PROHIBITED=0, UNVERIFIABLE=0, REVIEW=1, ALLOWED=1; RESULT: PASS |
| 16 | `python scripts/check_environment.py` | All PASS; RESULT: PASS |
| 17 | `python scripts/show_network_info.py` | Prints wildcard binds separately from candidate LAN IPv4s; labels the primary route |
| 18 | Manual grep audit (prohibited names, port literals) | Only docstrings, comments and help text; see `CONSTRAINT_AUDIT.md` |

### Checks that could not be completed
- Nothing that needs a real socket or thread. No such service exists yet.
- Running on macOS or Linux, which isn't available in this environment.
- Checking the `.docx`-sourced details (D10).

### Remaining work
See `CHECKPOINT.md` § Next steps and `PROJECT_PLAN.md` Phases 2–12.
