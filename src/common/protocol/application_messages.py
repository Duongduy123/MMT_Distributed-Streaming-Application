"""Application-level message categories (end-to-end meaning between users).

Source: assignment PDF, rubric Step 1 ("message types (e.g., AUTH, MSG, FILE)").
Status: SCAFFOLD -- names only. Values are ``enum.auto()`` and are NOT wire codes.
The final list and encoding belong to the protocol specification (docs/PROTOCOL_OVERVIEW.md).
"""

from __future__ import annotations

import enum


class ApplicationMessageType(enum.Enum):
    """What the user-level payload means. Independent of TCP/UDP framing."""

    AUTH = enum.auto()  # login / identity (carried on the control plane, D1)
    MSG = enum.auto()   # chat message: global (broadcast) or direct (unicast)
    FILE = enum.auto()  # file transfer: metadata on control plane, chunks on UDP data plane


class ChatScope(enum.Enum):
    """Delivery scope of a MSG (PDF section 4: broadcast and unicast)."""

    GLOBAL = enum.auto()
    DIRECT = enum.auto()
