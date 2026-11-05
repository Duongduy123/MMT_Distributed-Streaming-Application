"""Payload serialization contract. Status: SCAFFOLD.

The PDF allows JSON, XML or custom binary packing. The control plane (HTTP on 8080) is expected
to use JSON bodies (Phase 3). The UDP payload encoding is GATED ON D14 and must leave room for the
payload-encryption envelope (D9). Only the contract is defined here.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T")


class PayloadCodec(Protocol[T]):
    """Converts a structured value to/from bytes."""

    def to_bytes(self, value: T) -> bytes:
        """Serialize ``value``."""
        ...

    def from_bytes(self, data: bytes) -> T:
        """Deserialize; raise ``ProtocolError`` on malformed data."""
        ...
