"""UDP transport packet header. GATED ON D14 -- intentionally defines NO fields.

Two candidate sequence models exist and are incompatible (docs/DECISIONS.md D14):

Model A -- frame sequence (summary of reliability-tcp.docx / flowcontrol-tcp.docx):
    seq (4 B) per DATA frame, reused on retransmission; cumulative ack = LFR; up to 4 SACK
    ranges (1 + 8n B); rwnd (2 B); flags (1 B); timestamp (4 B); CRC32 (4 B).
    Windows LAR/LFS (sender) and LFR/LAF (receiver); ring buffer at ``seq % MaxSlotBuff``.

Model B -- packet number + stream offset (QUIC-like; the PDF references Google QUIC and asks
for head-of-line-blocking elimination; the existing CUBIC code assumes this):
    a new, never-reused packet number for every transmission (including retransmissions);
    ACK ranges over packet numbers; stream data addressed by (stream id, byte offset).

Unresolved even after choosing a model: endianness, timestamp unit, checksum coverage, MSS /
max payload, connection-id field, encryption envelope (D9).
"""

from __future__ import annotations

from typing import Protocol


class PacketHeaderCodec(Protocol):
    """Encodes/decodes a transport header. Concrete types are defined after D14."""

    def encode(self, header: object) -> bytes:
        """Serialize a header object to bytes."""
        ...

    def decode(self, data: bytes) -> tuple[object, int]:
        """Parse a header; return (header, number_of_bytes_consumed)."""
        ...


HEADER_FORMAT_STATUS = "GATED ON D14: no wire format is defined"
