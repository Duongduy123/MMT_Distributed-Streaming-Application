# Checkpoint

| Field | Value |
|---|---|
| **Current phase** | 1, Project scaffolding: **complete** |
| **Status** | **PROJECT SCAFFOLDING — VERIFIED** (this does *not* mean the network application is implemented) |
| **Date** | 2026-11-05 |
| **Last verified command** | `python -m unittest discover -s tests -t .` → `Ran 135 tests … OK`, and `python scripts/constraint_scan.py` → `RESULT: PASS` |
| **Git** | Not a git repository; nothing committed |

## Completed
- Two entry points with validated configuration and honest scaffold exit codes.
- Package structure for common, transport (shared), server and client.
- Existing CUBIC, Pacer and PacedSender copied byte-identical, with their tests passing in both locations.
- Separate network and dashboard binds (dashboard on loopback by default).
- Lifecycle with reverse-order rollback on partial startup failure.
- Two different vanilla-JS UI skeletons with labeled placeholders.
- AST constraint scanner, environment check and network-info script.
- Docs: architecture, plan, decision register D1–D14, constraint audit, protocol skeleton, review of the existing CUBIC code, source-document index.

## Current state
- **Works:**
  - CLI parsing and validation;
  - tests;
  - scripts;
  - static UI files (not served yet).
- **Does not exist yet:**
  - any listener;
  - the HTTP parser;
  - the control protocol;
  - the UDP transport;
  - relay, chat, files and encryption;
  - live UI.

## Outstanding decisions
| Blocks | Decision |
|---|---|
| **Phase 4–6** | **D14**: sequence model (frame seq vs packet number + stream offset) |
| Phase 7–8 finalization | D4 (initial window), D5 (pacing formula) |
| Phase 3, 10 | D2 (push mechanism: polling, long-poll or SSE) |
| Phase 11 | D9 (encryption dependency) |
| Final validation | D8 (instructor confirmation of TCP/UDP roles) |
| Before Phase 4 (recommended) | D10: review the 3 `.docx` files now in the root (`congestioncontrol`, `flowcontrol-tcp`, `reliability-tcp`) against D4/D5/D6/D14; add the 2 still missing |
| Team sign-off | D1 (HTTP/1.1 on 8080, provisional), D3, D6, D11 |

## Exact next steps
Do not start Phase 2 until the team says so.

1. Team meeting:
   - decide **D14**;
   - confirm D1, D3, D6 and D11;
   - pick the D4 preset and the D5 formula;
   - review the 3 `.docx` files now present and add the 2 missing ones (D10).
2. Ask the instructor about D8 and D9.
3. Phase 2 (can start after D1 and D11 are confirmed, independent of D14):
   - `HttpRequestParser.feed()`;
   - `RawHttpListener.start()/stop()` with a bounded worker pool and a partial-send loop;
   - static-file serving;
   - `ThreadTimerHost`, tested with the unchanged `PacedSender`.
