"""Send-queue types. Re-exported from the existing ``paced_sender`` to avoid duplication.

``PriorityPacketQueue`` keeps one FIFO per neutral priority class
(CONTROL > INTERACTIVE > BULK); the application maps chat -> INTERACTIVE and file chunks -> BULK
(architecture doc section 10.3).

TODO(Phase 8, D12): the existing queue is unbounded. Bounded capacity (per connection and per
relay destination) must be enforced by the owner before ``push`` -- without modifying the copied
paced_sender.py -- so a slow client cannot grow server memory without limit.
"""

from __future__ import annotations

from src.transport.paced_sender import OutgoingPacket, PriorityPacketQueue, SendPriority

__all__ = ["OutgoingPacket", "PriorityPacketQueue", "SendPriority"]
