"""Per-connection / per-direction transport state must never share mutable objects (D3)."""

from __future__ import annotations

import unittest

from src.transport.connection_state import TransportConnectionState
from src.transport.paced_sender import OutgoingPacket, SendPriority


class ConnectionStateIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a_b = TransportConnectionState(1, "A<->B")
        self.a_c = TransportConnectionState(2, "A<->C")

    def test_directions_and_connections_are_distinct_objects(self) -> None:
        self.assertIsNot(self.a_b.send, self.a_c.send)
        self.assertIsNot(self.a_b.receive, self.a_c.receive)
        self.assertIsNot(self.a_b.send.congestion, self.a_c.send.congestion)
        self.assertIsNot(self.a_b.send.queue, self.a_c.send.queue)

    def test_mutating_one_queue_does_not_affect_another(self) -> None:
        self.a_b.send.queue.push(OutgoingPacket(size=100, priority=SendPriority.BULK))
        self.assertEqual(len(self.a_b.send.queue), 1)
        self.assertEqual(len(self.a_c.send.queue), 0)

    def test_congestion_state_is_independent(self) -> None:
        before = self.a_c.send.congestion.cwnd()
        self.a_b.send.congestion.on_timeout(now=1.0)
        self.assertEqual(self.a_c.send.congestion.cwnd(), before)
        self.assertNotEqual(self.a_b.send.congestion.cwnd(), before)


if __name__ == "__main__":
    unittest.main()
