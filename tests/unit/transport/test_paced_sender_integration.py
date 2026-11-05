"""Integration of CubicController + Pacer + PacedSender with test doubles.

No network and no real transport: ``Harness`` plays the role of the reliability
layer (assigns packet numbers, owns bytes_in_flight) and of flow control.
"""

import itertools
import unittest

from tests.unit.transport.fakes import FakeLoop, PacketInfo, RttStats
from src.transport.congestion_control import CubicConfig, CubicController
from src.transport.paced_sender import (
    OutgoingPacket,
    PacedSender,
    PriorityPacketQueue,
    SendPriority,
)
from src.transport.pacer import Pacer

MSS = 1200
LARGE_CWND = CubicConfig(initial_cwnd_packets=1000, initial_ssthresh_packets=None)


class Harness:
    def __init__(
        self,
        cfg=None,
        drain_tokens=False,
        max_burst=10,
        capacity_packets=10,
        track_inflight=True,
    ):
        self.track_inflight = track_inflight
        self.loop = FakeLoop()
        self.cc = CubicController(cfg)
        self.pacer = Pacer(
            self.cc.pacing_rate(), self.loop.time(), capacity_packets=capacity_packets
        )
        if drain_tokens:
            self.pacer.try_consume(int(self.pacer.capacity), self.loop.time())
        self.queue = PriorityPacketQueue()
        self.in_flight = {}  # pn -> size (authoritative state lives here, not in cc)
        self.sent = []  # (time, packet, pn)
        self.flow_ok = True
        self._pn = 0
        self.sender = PacedSender(
            self.cc,
            self.pacer,
            self.queue,
            self._transmit,
            lambda: sum(self.in_flight.values()),
            self.loop,
            flow_allows=lambda _p: self.flow_ok,
            max_burst_packets=max_burst,
        )

    def _transmit(self, pkt):
        self._pn += 1
        if pkt.congestion_controlled and self.track_inflight:
            self.in_flight[self._pn] = pkt.size
        self.sent.append((self.loop.time(), pkt, self._pn))
        return self._pn

    def enqueue(self, priority, n=1, size=MSS, tag=None, controlled=True):
        for i in range(n):
            self.queue.push(
                OutgoingPacket(size, priority, controlled, payload=(tag, i))
            )

    def ack(self, pns, srtt=0.1):
        pkts = [PacketInfo(pn, self.in_flight.pop(pn)) for pn in pns]
        self.cc.on_ack(pkts, RttStats(srtt), self.loop.time())
        self.sender.kick()

    def tags(self):
        return [p.payload[0] for _, p, _ in self.sent]


class CwndAndTokenGatingTests(unittest.TestCase):
    def test_cwnd_blocks_even_with_full_bucket(self):
        h = Harness()  # cwnd 2 packets, bucket full (10 packets)
        h.enqueue(SendPriority.BULK, 10)
        h.sender.kick()
        self.assertEqual(len(h.sent), 2)
        self.assertEqual(sum(h.in_flight.values()), h.cc.cwnd())
        self.assertFalse(
            h.sender.timer_armed
        )  # blocked on cwnd: wait for an ACK, no timer
        self.assertEqual(h.loop.pending(), 0)

    def test_tokens_block_even_with_open_cwnd(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.enqueue(SendPriority.BULK, 5)
        h.sender.kick()
        self.assertEqual(len(h.sent), 0)
        self.assertTrue(h.sender.timer_armed)
        self.assertEqual(h.loop.pending(), 1)
        # srtt 0.333 default: SS rate = 2 * 1_200_000 / 0.333 B/s: wake at granularity floor
        self.assertAlmostEqual(h.loop.next_when() - h.loop.time(), 0.001, places=6)
        h.loop.advance(0.001)
        self.assertGreater(len(h.sent), 0)

    def test_slow_pacing_spreads_packets_over_time(self):
        cfg = CubicConfig(initial_cwnd_packets=1000, initial_ssthresh_packets=None)
        h = Harness(cfg, drain_tokens=True)
        h.cc.on_ack([], RttStats(1000.0), h.loop.time())  # srtt 1000 s -> rate 2400 B/s
        h.pacer.set_rate(h.cc.pacing_rate(), h.loop.time())
        self.assertAlmostEqual(h.pacer.rate, 2 * 1_200_000 / 1000.0)
        h.enqueue(SendPriority.BULK, 20)
        h.sender.kick()
        h.loop.advance(10.0)  # 10 s * 2400 B/s = 24 000 bytes = 20 packets worth
        times = [t for t, _, _ in h.sent]
        self.assertEqual(len(h.sent), 20)
        gaps = [b - a for a, b in itertools.pairwise(times) if b > a]
        self.assertTrue(
            all(abs(g - 0.5) < 1e-6 for g in gaps), gaps
        )  # 1200 B / 2400 B/s

    def test_total_bytes_bounded_by_rate_and_bucket(self):
        # in-flight tracking off = "instant ACKs", so only the pacer limits the rate
        h = Harness(LARGE_CWND, drain_tokens=True, track_inflight=False)
        h.cc.on_ack(
            [], RttStats(1.0), h.loop.time()
        )  # rate = 2 * 1.2e6 / 1 = 2.4e6 B/s
        h.enqueue(SendPriority.BULK, 5000)
        start = h.loop.time()
        h.sender.kick()
        for _ in range(100):
            h.loop.advance(0.01)
        sent_bytes = sum(p.size for _, p, _ in h.sent)
        budget = h.pacer.rate * (h.loop.time() - start) + h.pacer.capacity
        self.assertLessEqual(sent_bytes, budget + 1)
        self.assertGreater(sent_bytes, 0.9 * h.pacer.rate * (h.loop.time() - start))

    def test_burst_never_exceeds_ten_packets_per_turn(self):
        h = Harness(LARGE_CWND, capacity_packets=25)  # bucket could allow 25
        h.enqueue(SendPriority.BULK, 40)
        h.sender.kick()
        self.assertEqual(len(h.sent), 10)
        self.assertTrue(h.sender.timer_armed)  # yields to the loop, no inner spin
        self.assertTrue(h.loop.step())  # one more turn: another 10, not 15
        self.assertEqual(len(h.sent), 20)
        self.assertTrue(h.loop.step())  # last 5 tokens of the 25-packet bucket
        self.assertEqual(len(h.sent), 25)

    def test_sender_reports_packets_to_controller(self):
        h = Harness()
        h.enqueue(SendPriority.BULK, 2)
        h.sender.kick()
        # pn 1 and 2 were sent; a loss of pn 2 is in the current period only if newer
        # than the recovery boundary, which starts at -1 -> it must reduce.
        h.cc.on_loss([PacketInfo(2)], h.loop.time())
        self.assertTrue(h.cc.in_recovery)


class ControllerFeedbackTests(unittest.TestCase):
    def test_ack_updates_cubic_and_pacer_rate(self):
        h = Harness()
        h.enqueue(SendPriority.BULK, 10)
        h.sender.kick()
        self.assertEqual(sorted(h.in_flight), [1, 2])
        before = h.pacer.rate
        h.ack([1, 2], srtt=0.1)
        self.assertEqual(h.cc.cwnd(), 4 * MSS)
        self.assertAlmostEqual(h.pacer.rate, 2 * 4800 / 0.1)  # 96 000 B/s
        self.assertGreater(h.pacer.rate, before)
        self.assertEqual(len(h.sent), 2 + 4)  # window reopened to 4 packets in flight

    def test_loss_reduces_cwnd_and_pacing_rate(self):
        h = Harness()
        h.enqueue(SendPriority.BULK, 200)
        h.sender.kick()
        for _ in range(2):  # 2 -> 4 -> 8 packets (= ssthresh, now congestion avoidance)
            h.ack(sorted(h.in_flight))
            h.loop.advance(0.1)  # let the pacer refill and its timer fire
        self.assertEqual(h.cc.cwnd(), 8 * MSS)
        self.assertAlmostEqual(h.pacer.rate, 1.2 * 9600 / 0.1)
        h.cc.on_loss([PacketInfo(max(h.in_flight))], h.loop.time())
        h.sender.kick()
        self.assertEqual(h.cc.cwnd(), 5 * MSS)
        self.assertAlmostEqual(h.pacer.rate, 1.2 * 6000 / 0.1)  # 72 000 B/s
        self.assertLessEqual(sum(h.in_flight.values()), 8 * MSS)

    def test_timeout_returns_to_slow_start_through_the_gate(self):
        h = Harness()
        h.enqueue(SendPriority.BULK, 50)
        h.sender.kick()
        for _ in range(2):
            h.ack(sorted(h.in_flight))
        h.cc.on_timeout(h.loop.time())
        h.sender.kick()
        self.assertEqual(h.cc.cwnd(), MSS)
        self.assertTrue(h.cc.in_slow_start)
        self.assertAlmostEqual(h.pacer.rate, 2 * MSS / 0.1)
        in_flight_before = sum(h.in_flight.values())
        n_before = len(h.sent)
        h.loop.advance(1.0)
        # old packets still count as in flight (the reliability layer owns that
        # accounting), so nothing new may leave while bytes_in_flight >= cwnd
        self.assertGreaterEqual(in_flight_before, MSS)
        self.assertEqual(len(h.sent), n_before)

    def test_rate_change_rearms_single_timer(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.cc.on_ack([], RttStats(1000.0), h.loop.time())
        h.enqueue(SendPriority.BULK, 5)
        h.sender.kick()
        first = h.loop.next_when()
        self.assertEqual(h.loop.pending(), 1)
        h.cc.on_ack([], RttStats(500.0), h.loop.time())  # rate doubles
        h.sender.kick()
        self.assertEqual(h.loop.pending(), 1)  # old timer cancelled, not stacked
        self.assertLess(h.loop.next_when(), first)


class PriorityTests(unittest.TestCase):
    def test_chat_goes_before_file_at_next_tick(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.enqueue(SendPriority.BULK, 50, tag="file")
        h.sender.kick()
        self.assertEqual(len(h.sent), 0)
        h.enqueue(SendPriority.INTERACTIVE, 1, tag="chat")  # created while waiting
        h.sender.kick()
        h.loop.advance(0.5)
        self.assertGreater(len(h.sent), 1)
        self.assertEqual(h.tags()[0], "chat")
        self.assertTrue(all(t == "file" for t in h.tags()[1:]))

    def test_file_order_within_stream_is_preserved(self):
        h = Harness(LARGE_CWND)
        h.enqueue(SendPriority.BULK, 30, tag="file")
        h.enqueue(SendPriority.INTERACTIVE, 3, tag="chat")
        h.sender.kick()
        h.loop.advance(1.0)
        files = [p.payload[1] for _, p, _ in h.sent if p.payload[0] == "file"]
        chats = [p.payload[1] for _, p, _ in h.sent if p.payload[0] == "chat"]
        self.assertEqual(files, sorted(files))
        self.assertEqual(chats, [0, 1, 2])
        pns = [pn for _, _, pn in h.sent]
        self.assertEqual(pns, sorted(pns))

    def test_full_file_queue_cannot_starve_chat(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.cc.on_ack([], RttStats(10.0), h.loop.time())  # slow: 240 000 B/s
        h.enqueue(SendPriority.BULK, 100_000, tag="file")
        h.sender.kick()
        created = {}
        for i in range(30):
            h.enqueue(SendPriority.INTERACTIVE, 1, tag=f"chat{i}")
            created[f"chat{i}"] = h.loop.time()
            h.sender.kick()
            h.loop.advance(0.01)
        sent_at = {
            p.payload[0]: t for t, p, _ in h.sent if p.payload[0].startswith("chat")
        }
        self.assertEqual(len(sent_at), 30)
        for tag, t_created in created.items():
            # sent no later than the first pacing tick after creation
            self.assertLessEqual(sent_at[tag] - t_created, 0.01 + 1e-9, tag)

    def test_blocked_chat_is_not_overtaken_by_file(self):
        h = Harness()  # cwnd = 2 packets
        h.enqueue(SendPriority.BULK, 2, tag="file")
        h.sender.kick()  # fills the window with file packets
        h.enqueue(SendPriority.INTERACTIVE, 1, tag="chat")
        h.enqueue(
            SendPriority.BULK, 1, tag="file2", size=100
        )  # small: would fit nowhere
        h.sender.kick()
        self.assertEqual(h.tags(), ["file", "file"])
        h.ack([1])
        self.assertEqual(h.tags()[2], "chat")

    def test_ack_only_packets_bypass_cwnd_and_are_not_in_flight(self):
        h = Harness()
        h.enqueue(SendPriority.BULK, 2, tag="file")
        h.sender.kick()  # window full
        h.enqueue(SendPriority.CONTROL, 1, size=40, tag="ack", controlled=False)
        h.sender.kick()
        self.assertEqual(h.tags(), ["file", "file", "ack"])
        self.assertEqual(sum(h.in_flight.values()), 2 * MSS)  # ACK not counted


class FlowControlTests(unittest.TestCase):
    def test_flow_control_is_not_bypassed(self):
        h = Harness(LARGE_CWND)
        h.flow_ok = False
        h.enqueue(SendPriority.BULK, 5)
        h.enqueue(SendPriority.INTERACTIVE, 1)
        h.sender.kick()
        self.assertEqual(len(h.sent), 0)
        self.assertFalse(h.sender.timer_armed)
        h.flow_ok = True  # MAX_STREAM_DATA arrived
        h.sender.kick()
        self.assertEqual(len(h.sent), 6)


class TimerTests(unittest.TestCase):
    def test_empty_queue_never_arms_a_timer(self):
        h = Harness(LARGE_CWND)
        for _ in range(100):
            h.sender.kick()
        h.loop.advance(5.0)
        self.assertEqual(h.loop.call_at_count, 0)
        self.assertEqual(h.loop.pending(), 0)
        self.assertEqual(h.sent, [])

    def test_repeated_kicks_keep_one_timer(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.enqueue(SendPriority.BULK, 5)
        for _ in range(50):
            h.sender.kick()
        self.assertEqual(h.loop.pending(), 1)
        self.assertEqual(h.loop.call_at_count, 1)  # same wake time: timer reused

    def test_timer_stops_when_queue_drains(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.enqueue(SendPriority.BULK, 3)
        h.sender.kick()
        h.loop.advance(1.0)
        self.assertEqual(len(h.sent), 3)
        self.assertEqual(h.loop.pending(), 0)
        self.assertFalse(h.sender.timer_armed)

    def test_no_busy_loop_when_tokens_never_arrive(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.pacer.set_rate(0.0, h.loop.time())
        h.cc.on_ack([], RttStats(1e12), h.loop.time())  # rate ~0 but sender resyncs it
        h.enqueue(SendPriority.BULK, 3)
        h.sender.kick()
        h.loop.advance(10.0)
        self.assertLess(h.loop.call_at_count, 20)

    def test_close_cancels_timer_and_stops_sending(self):
        h = Harness(LARGE_CWND, drain_tokens=True)
        h.enqueue(SendPriority.BULK, 5)
        h.sender.kick()
        self.assertEqual(h.loop.pending(), 1)
        h.sender.close()
        self.assertEqual(h.loop.pending(), 0)
        h.sender.kick()
        h.loop.advance(10)
        self.assertEqual(h.sent, [])
        self.assertEqual(h.loop.pending(), 0)

    def test_transmit_must_return_pn_for_controlled_packets(self):
        h = Harness()
        h.sender._transmit = lambda pkt: None
        h.enqueue(SendPriority.BULK, 1)
        with self.assertRaises(ValueError):
            h.sender.kick()


class ConnectionIndependenceTests(unittest.TestCase):
    def test_pacer_state_is_per_connection(self):
        a = Harness(LARGE_CWND, drain_tokens=True)
        b = Harness(LARGE_CWND)
        a.enqueue(SendPriority.BULK, 5)
        b.enqueue(SendPriority.BULK, 5)
        a.sender.kick()
        b.sender.kick()
        self.assertEqual(len(a.sent), 0)  # a is out of tokens
        self.assertEqual(len(b.sent), 5)  # b is unaffected
        self.assertEqual(b.pacer.tokens(b.loop.time()), 10 * MSS - 5 * MSS)


if __name__ == "__main__":
    unittest.main()
