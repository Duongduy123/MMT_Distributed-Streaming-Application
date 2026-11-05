# Review of the existing CUBIC / Pacer / PacedSender code

**Scope:** the code that existed in `congestion_control/` before scaffolding (identical to `lovvit_cc_cubic_pacer.zip`). It was copied into `src/transport/` **without modification**.

**Status:** tests pass in both locations. **Assignment compliance is UNVERIFIED** (D13). Passing tests show only that the code does what its own tests expect, not that it matches the team's specification.

## 1. Manifest (SHA-256, recorded before copying)

| File (original) | SHA-256 |
|---|---|
| `congestion_control/docs/congestion_control.md` | `0d1857b2a4c47e6d60c4a5cc15e770a8e895767c8880567247c4eb124ad8678e` |
| `congestion_control/tests/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |
| `congestion_control/tests/fakes.py` | `fa4fb1c11d7200f812c21884a35529386e64fb87d4005279ee74853c6a2ba0ae` |
| `congestion_control/tests/test_congestion_control.py` | `ff6bf5de23bef7e784ded3c0c685f76da4ba404592a1dd8136808b09aa6427ad` |
| `congestion_control/tests/test_paced_sender_integration.py` | `b6ffbf12638d23c483f1f960e1eb1c2f00b5d8e397263235d93e9941ba63a157` |
| `congestion_control/tests/test_pacer.py` | `7f3be17eb52eeca62bc8e3dc8d758095ab99d5151db0468dea6cab8ade2beebc` |
| `congestion_control/transport/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |
| `congestion_control/transport/congestion_control.py` | `467c36aaff4e96b31dafe98ea9351d26575e5afe2ab1194da1b7ac2b69468e8b` |
| `congestion_control/transport/paced_sender.py` | `e9732b8511e1113a89f13defa246ccceacf8ed1f8b692a4566744e633e48f69f` |
| `congestion_control/transport/pacer.py` | `f713f3caeb5494a2203e66328d95d868ea3bc10eb94f226348fdd3cb80706b6b` |
| `lovvit_cc_cubic_pacer.zip` | `8bd6ee21f7be2a49d22d334588ac2ea26e2d87a22f17e256f8eb04bb3a8ad161` |

## 2. Copy verification

| Copy | Comparison | Result |
|---|---|---|
| `src/transport/congestion_control.py` | SHA-256 vs original | **IDENTICAL** |
| `src/transport/pacer.py` | SHA-256 vs original | **IDENTICAL** |
| `src/transport/paced_sender.py` | SHA-256 vs original | **IDENTICAL** |
| `tests/unit/transport/fakes.py` | SHA-256 vs original | **IDENTICAL** |
| `tests/unit/transport/test_congestion_control.py` | difflib: 6 changed lines, all `from …` imports | IMPORT-ONLY (new hash `30a241f728250b3b…`) |
| `tests/unit/transport/test_pacer.py` | difflib: 2 changed lines, all imports | IMPORT-ONLY (`29a6ea478016df94…`) |
| `tests/unit/transport/test_paced_sender_integration.py` | difflib: 8 changed lines, all imports | IMPORT-ONLY (`cd65ad74f7e9b2d1…`) |

**Import rewrite rule:**

- `from transport.X` → `from src.transport.X`
- `from tests.fakes` → `from tests.unit.transport.fakes`

`paced_sender.py` imports its siblings relatively (`.congestion_control`, `.pacer`), so it needed no change.

**Originals re-hashed after copying and testing:** all 11 hashes are unchanged. Running the original tests creates `__pycache__/` folders inside `congestion_control/`; these were deleted to restore the folder to its inspected state.

## 3. Independent test runs (2026-11-05, Python 3.12.10, Windows 11)

| Run | Command | Result |
|---|---|---|
| Original | `cd congestion_control && python -m unittest discover -s tests -t .` | 92 tests, OK |
| Copies only | `python -m unittest discover -s tests/unit/transport -t .` | 92 tests, OK |
| Full suite | `python -m unittest discover -s tests -t .` | 135 tests, OK |

## 4. Differences from the specification

The reference is ARCH §9–10. Details from `congestioncontrol.docx` are summary-sourced (D10).

| Aspect | Existing code | Specification (ARCH) | Assessment |
|---|---|---|---|
| Initial cwnd / ssthresh | Default `CubicConfig()`: 2 / 8 MSS. Preset `design_doc()`: 10 MSS / ∞ | §9.6 lists both as a conflict | **D4**: the team must pick one |
| β, C | 0.7, 0.4 | §9.2: 0.7, 0.4 | Matches |
| Slow start | `cwnd += acked_bytes`; clamped to land exactly on `ssthresh`, which starts an epoch | §9.2: +1 packet per ACK (≈ doubling per RTT) | Equivalent in bytes; the clamp is a code choice |
| Congestion-avoidance growth | W(t) = C(t−K)³ + W_max, **plus** the RFC 9438 Reno-friendly `W_est` and a 1.5× per-ACK target cap | §9.2: W(t) and K only | **Additions not in the spec**; the team should accept or remove them |
| Epoch without loss history | `W_max = cwnd`, `K = 0` when slow start reaches ssthresh | Not specified | Assumption |
| Fast-loss reduction | `W_max = cwnd`; `cwnd = ssthresh = max(floor(cwnd/MSS·0.7)·MSS, 2 MSS)`; at most once per recovery period (boundary = largest pn sent) | §9.3: β = 0.7, at most once per recovery | Matches in substance; the MSS flooring and 2-MSS minimum are code choices |
| Timeout | `ssthresh = max(floor(0.7·cwnd), 2 MSS)`; `cwnd = 1 MSS`; repeated RTOs keep the first W_max | §9.4: same values | Matches; the repeated-RTO rule is an addition |
| Persistent congestion | `cwnd = 2 MSS`; `ssthresh ≥ 3 MSS` | Not specified | Assumption |
| Pacing rate | `2.0·cwnd/srtt` in slow start, `1.2·cwnd/srtt` otherwise; `srtt` defaults to 0.333 s | §9.7: conflict between `gain·BtlBw` and this formula | **D5**. The 0.333 s default is not stated in ARCH (unsourced). ARCH's initial RTO is 1 s |
| MSS | 1200 bytes | Not finalized | D6 / D14 |
| Pacer | Token bucket of 10 MSS, starts full, `min(size, capacity)` cost, monotonic `now` | §10.1: 10-packet bucket, monotonic time | Matches; clamping oversize packets is an addition |
| Send gate order | Flow credit → `bytes_in_flight + size ≤ cwnd` → tokens; stops at the first blocked packet; ACK-only packets skip cwnd and pacing | §9.5, §10.2 | Matches |
| Priority | CONTROL > INTERACTIVE > BULK, FIFO within each class | §10.3: control/chat before file data | Matches |
| Packet identity | `pn` unique per transmission, never reused | Model A reuses `seq` on retransmission | **D14 conflict** |
| Timer host | `TimerHostLike`: `time()`, `call_at(when, cb)`, `handle.cancel()`; the docstring says an asyncio loop satisfies it | Team: threading, no asyncio | Resolved by the `ThreadTimerHost` design (D11); the code does **not** import asyncio |
| Thread safety | None; `_running` is a re-entrancy guard only | Multiple threads in each process | Must be confined to the scheduler thread (D11) |
| Bounded queues | `PriorityPacketQueue` is unbounded | ARCH §13.3: queues must be bounded | The owner must enforce the bound before `push` (D12) |

## 5. What must happen before CUBIC/Pacer is marked compliant
1. Resolve D14. If Model A is chosen, the CUBIC recovery-boundary logic needs a unique per-transmission identifier that is separate from the frame `seq`.
2. Resolve D4 (choose the preset) and D5 (choose the pacing formula).
3. Accept or remove the RFC 9438 additions (Reno-friendly estimate, 1.5× cap) and the persistent-congestion values.
4. Implement `ThreadTimerHost` and add a `PacedSender` + `ThreadTimerHost` test that runs on real threads.
