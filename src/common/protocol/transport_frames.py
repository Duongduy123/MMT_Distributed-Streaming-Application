"""Custom UDP transport frame kinds. GATED ON D14.

Source: architecture doc section 7.2 (flags: DATA, ACK, WND_PROBE, RETX), summary-sourced from
reliability-tcp.docx (not available in this workspace, see D10).
Status: SCAFFOLD -- names only. Whether RETX is a distinct kind, whether ACK carries SACK blocks
or packet-number ranges, and every numeric code depend on the sequence model chosen in D14.
"""

from __future__ import annotations

import enum


class TransportFrameKind(enum.Enum):
    """Transport-layer frame kinds. Never mixed with application or control types."""

    DATA = enum.auto()
    ACK = enum.auto()
    WND_PROBE = enum.auto()  # zero-window probe (architecture doc section 7.6)
    RETX = enum.auto()       # listed as a flag in the summary; may disappear under D14 Model B
