import math
import unittest

from tests.unit.transport.fakes import PacketInfo as P
from tests.unit.transport.fakes import RttStats
from src.transport.congestion_control import (
    CubicConfig,
    CubicController,
    cubic_k,
    cubic_window,
    reno_friendly_alpha,
)

MSS = 1200
T0 = 100.0  # non-zero base time so epoch bugs cannot hide behind t == 0


def ctrl(cfg=None):
    return CubicController(cfg)


def to_ca_at_8(c, now=T0):
    """Drive the default controller 2 -> 4 -> 8 packets (mmt-ass1 timeline)."""
    c.on_ack([P(1), P(2)], RttStats(0.1), now)
    c.on_ack([P(3), P(4), P(5), P(6)], RttStats(0.1), now + 0.1)


class InitialStateTests(unittest.TestCase):
    def test_default_values(self):
        c = ctrl()
        self.assertEqual(c.config.mss, 1200)
        self.assertEqual(c.config.beta, 0.7)
        self.assertEqual(c.config.c, 0.4)
        self.assertEqual(c.cwnd(), 2 * MSS)
        self.assertEqual(c.ssthresh(), 8 * MSS)
        self.assertTrue(c.in_slow_start)
        self.assertIsInstance(c.cwnd(), int)

    def test_design_doc_preset(self):
        c = ctrl(CubicConfig.design_doc())
        self.assertEqual(c.cwnd(), 10 * MSS)
        self.assertTrue(math.isinf(c.ssthresh()))
        self.assertTrue(c.in_slow_start)


class SlowStartTests(unittest.TestCase):
    def test_one_ack_adds_acked_bytes(self):
        c = ctrl()
        c.on_ack([P(1)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 3 * MSS)

    def test_doubles_per_rtt_and_lands_on_ssthresh(self):
        # mmt-ass1 section 6: 2 -> 4 -> 8 = ssthresh, then congestion avoidance.
        c = ctrl()
        c.on_ack([P(1), P(2)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 4 * MSS)
        c.on_ack([P(3), P(4), P(5), P(6)], RttStats(), T0 + 0.1)
        self.assertEqual(c.cwnd(), 8 * MSS)
        self.assertFalse(c.in_slow_start)

    def test_does_not_overshoot_ssthresh(self):
        c = ctrl()
        c.on_ack([P(i) for i in range(1, 20)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 8 * MSS)

    def test_partial_ack_adds_only_acked_bytes(self):
        c = ctrl()
        c.on_ack([P(1, 600)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 2 * MSS + 600)
        c.on_ack([P(2, 300), P(3, 100)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 2 * MSS + 1000)

    def test_transition_starts_epoch_without_loss_history(self):
        c = ctrl()
        to_ca_at_8(c)
        self.assertEqual(c.epoch_start, T0 + 0.1)
        self.assertEqual(c.w_max(), 8 * MSS)  # W_max = cwnd at transition
        self.assertEqual(c.k, 0.0)  # convex probing, no plateau wait

    def test_on_packet_sent_does_not_change_window(self):
        c = ctrl()
        for pn in range(1, 6):
            c.on_packet_sent(pn, MSS, T0)
        self.assertEqual(c.cwnd(), 2 * MSS)


class CubicFormulaTests(unittest.TestCase):
    def test_k_values(self):
        self.assertAlmostEqual(cubic_k(8, 0.7, 0.4), 1.8171205928, places=9)
        self.assertAlmostEqual(cubic_k(10, 0.7, 0.4), 1.9574338205, places=9)
        self.assertEqual(cubic_k(0, 0.7, 0.4), 0.0)

    def test_window_function_wmax_8(self):
        k = cubic_k(8, 0.7, 0.4)
        self.assertAlmostEqual(
            cubic_window(0, k, 8, 0.4), 5.6, places=9
        )  # = 0.7 * W_max
        self.assertAlmostEqual(cubic_window(1.0, k, 8, 0.4), 7.7817679873, places=8)
        self.assertAlmostEqual(
            cubic_window(k, k, 8, 0.4), 8.0, places=12
        )  # plateau at W_max
        self.assertAlmostEqual(cubic_window(2 * k, k, 8, 0.4), 10.4, places=9)

    def test_window_function_wmax_10(self):
        k = cubic_k(10, 0.7, 0.4)
        self.assertAlmostEqual(cubic_window(0, k, 10, 0.4), 7.0, places=9)
        self.assertAlmostEqual(cubic_window(2 * k, k, 10, 0.4), 13.0, places=9)

    def test_controller_uses_segments_not_bytes(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_packet_sent(20, MSS, T0 + 0.2)
        c.on_loss([P(20)], T0 + 0.3)
        self.assertAlmostEqual(c.k, 1.8171205928, places=9)
        self.assertAlmostEqual(c.w_cubic_packets(0.0), 5.6, places=9)
        self.assertAlmostEqual(c.w_cubic_packets(c.k), 8.0, places=9)
        self.assertAlmostEqual(c.w_cubic_packets(2 * c.k), 10.4, places=9)

    def test_reno_alpha(self):
        self.assertAlmostEqual(reno_friendly_alpha(0.7), 0.5294117647, places=9)


class FastLossTests(unittest.TestCase):
    def setUp(self):
        self.c = ctrl()
        to_ca_at_8(self.c)
        for pn in range(1, 15):
            self.c.on_packet_sent(pn, MSS, T0 + 0.2)
        self.t_loss = T0 + 0.3

    def test_wmax_saved_and_window_reduced(self):
        # mmt-ass1 timeline: W_max = 8, ssthresh = cwnd = floor(8 * 0.7) = 5 packets
        self.c.on_loss([P(8)], self.t_loss)
        self.assertEqual(self.c.w_max(), 8 * MSS)
        self.assertEqual(self.c.cwnd(), 5 * MSS)
        self.assertEqual(self.c.ssthresh(), 5 * MSS)
        self.assertTrue(self.c.in_recovery)
        self.assertFalse(self.c.in_slow_start)
        self.assertEqual(self.c.epoch_start, self.t_loss)

    def test_no_repeated_reduction_in_same_recovery(self):
        self.c.on_loss([P(8)], self.t_loss)
        self.c.on_loss([P(8)], self.t_loss + 0.01)  # duplicate report
        self.c.on_loss([P(11), P(12)], self.t_loss + 0.02)  # sent before recovery began
        self.assertEqual(self.c.cwnd(), 5 * MSS)
        self.assertEqual(self.c.w_max(), 8 * MSS)

    def test_loss_after_recovery_boundary_reduces_again(self):
        self.c.on_loss([P(8)], self.t_loss)
        self.c.on_packet_sent(15, MSS, self.t_loss + 0.01)
        self.c.on_loss([P(15)], self.t_loss + 0.2)  # sent after the first reduction
        self.assertEqual(self.c.w_max(), 5 * MSS)
        self.assertEqual(self.c.cwnd(), 3 * MSS)  # floor(5 * 0.7) = 3

    def test_empty_loss_list_is_noop(self):
        self.c.on_loss([], self.t_loss)
        self.assertEqual(self.c.cwnd(), 8 * MSS)
        self.assertFalse(self.c.in_recovery)

    def test_minimum_window_floor(self):
        c = ctrl()
        c.on_packet_sent(1, MSS, T0)
        c.on_loss([P(1)], T0)  # cwnd 2 packets: floor(1.4) = 1 -> floored to 2
        self.assertEqual(c.cwnd(), 2 * MSS)

    def test_recovery_boundary_blocks_growth_until_new_packet_acked(self):
        self.c.on_loss([P(8)], self.t_loss)
        for pn in range(9, 15):  # sent before the loss: ACKs must not grow cwnd
            self.c.on_ack([P(pn)], RttStats(1.0), self.t_loss + 0.1)
        self.assertEqual(self.c.cwnd(), 5 * MSS)
        self.assertTrue(self.c.in_recovery)
        self.c.on_packet_sent(15, MSS, self.t_loss + 0.05)  # the retransmission
        # ACK 1.0 s after the loss: t = 1.0, srtt = 1.0
        # W_cubic(1.0)=7.7818, W_est=5.5294, target=min(7.7818, 1.5*5)=7.5
        # cwnd += (7.5-5)/5 * 1 segment = 0.5  -> 5.5 segments = 6600 bytes
        self.c.on_ack([P(15)], RttStats(1.0), self.t_loss + 1.0)
        self.assertFalse(self.c.in_recovery)
        self.assertEqual(self.c.cwnd(), 6600)


class CongestionAvoidanceTests(unittest.TestCase):
    def big_after_loss(self):
        """W_max = 100 segments, cwnd = 70 segments, epoch at T0."""
        c = ctrl(CubicConfig(initial_cwnd_packets=100, initial_ssthresh_packets=None))
        c.on_packet_sent(1, MSS, T0)
        c.on_loss([P(1)], T0)
        self.assertEqual(c.cwnd(), 70 * MSS)
        c.on_packet_sent(2, MSS, T0)
        return c

    def test_cubic_region_chosen_when_larger(self):
        c = self.big_after_loss()
        # t=1, srtt=2: W_cubic=86.6808 > W_est=70.2647 -> cubic
        # cwnd += (86.6808-70)/70 = 0.238297 segments
        c.on_ack([P(2)], RttStats(2.0), T0 + 1.0)
        self.assertEqual(c.cwnd(), 84285)

    def test_reno_friendly_region_chosen_when_larger(self):
        c = self.big_after_loss()
        # t=1, srtt=0.03: W_est=70+0.52941*33.333=87.6471 > W_cubic=86.6808
        # cwnd += (87.6471-70)/70 = 0.252101 segments
        self.assertAlmostEqual(c.w_est_packets(1.0, 0.03), 87.6470588, places=6)
        self.assertGreater(c.w_est_packets(1.0, 0.03), c.w_cubic_packets(1.0))
        c.on_ack([P(2)], RttStats(0.03), T0 + 1.0)
        self.assertEqual(c.cwnd(), 84302)

    def test_target_capped_at_1_5x_cwnd(self):
        c = self.big_after_loss()
        # t=8 (W_cubic=121.65 > 1.5*70=105): target limited to 105
        # cwnd += (105-70)/70 = 0.5 segment
        c.on_ack([P(2)], RttStats(2.0), T0 + 8.0)
        self.assertEqual(c.cwnd(), 84000 + 600)

    def test_epoch_not_reset_by_acks(self):
        c = self.big_after_loss()
        for i in range(2, 10):
            c.on_packet_sent(i, MSS, T0 + 0.1 * i)
            c.on_ack([P(i)], RttStats(0.1), T0 + 0.1 * i)
        self.assertEqual(c.epoch_start, T0)

    def test_cwnd_monotone_and_finite_over_long_run(self):
        c = self.big_after_loss()
        prev = c.cwnd()
        for i in range(2, 4000):
            c.on_packet_sent(i, MSS, T0 + 0.01 * i)
            c.on_ack([P(i)], RttStats(0.05), T0 + 0.01 * i)
            cur = c.cwnd()
            self.assertGreaterEqual(cur, prev)
            self.assertTrue(math.isfinite(c.pacing_rate()))
            prev = cur
        self.assertGreater(prev, 100 * MSS)  # passed W_max and kept probing
        self.assertLessEqual(prev, c.config.max_cwnd_bytes)

    def test_deterministic(self):
        def run():
            c = self.big_after_loss()
            for i in range(2, 200):
                c.on_packet_sent(i, MSS, T0 + 0.02 * i)
                c.on_ack([P(i)], RttStats(0.07), T0 + 0.02 * i)
            return c.cwnd()

        self.assertEqual(run(), run())

    def test_ack_exactly_at_epoch_start(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_packet_sent(20, MSS, T0 + 0.2)
        c.on_loss([P(20)], T0 + 0.3)  # cwnd 5 segments, W(0) = 5.6
        c.on_packet_sent(21, MSS, T0 + 0.3)
        # t == 0: target 5.6 -> cwnd += (5.6-5)/5 = 0.12 segment = 144 bytes
        c.on_ack([P(21)], RttStats(0.1), T0 + 0.3)
        self.assertEqual(c.cwnd(), 6144)

    def test_ack_timestamp_before_epoch_is_clamped(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_packet_sent(20, MSS, T0 + 0.2)
        c.on_loss([P(20)], T0 + 0.3)
        c.on_packet_sent(21, MSS, T0 + 0.3)
        c.on_ack([P(21)], RttStats(0.1), T0 + 0.1)  # earlier than the epoch
        self.assertEqual(c.cwnd(), 6144)  # behaves exactly like t == 0


class TimeoutTests(unittest.TestCase):
    def test_timeout_from_8_packets(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_timeout(T0 + 0.5)
        self.assertEqual(c.w_max(), 8 * MSS)
        self.assertEqual(c.ssthresh(), 5 * MSS)  # max(floor(5.6), 2)
        self.assertEqual(c.cwnd(), 1 * MSS)
        self.assertTrue(c.in_slow_start)
        self.assertFalse(c.in_recovery)

    def test_timeout_ssthresh_floor_of_two_packets(self):
        c = ctrl()  # cwnd = 2 packets: floor(1.4) = 1 -> max(1, 2) = 2
        c.on_timeout(T0)
        self.assertEqual(c.ssthresh(), 2 * MSS)
        self.assertEqual(c.cwnd(), MSS)

    def test_slow_start_then_cubic_after_timeout(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_timeout(T0 + 0.5)
        c.on_packet_sent(30, MSS, T0 + 0.6)
        t = T0 + 0.7
        c.on_ack([P(30)], RttStats(0.1), t)  # 1 -> 2 packets
        self.assertEqual(c.cwnd(), 2 * MSS)
        self.assertTrue(c.in_slow_start)
        for pn in (31, 32, 33):
            c.on_packet_sent(pn, MSS, t)
            c.on_ack([P(pn)], RttStats(0.1), t)
        self.assertEqual(c.cwnd(), 5 * MSS)  # reached ssthresh
        self.assertFalse(c.in_slow_start)
        self.assertEqual(c.epoch_start, t)
        self.assertAlmostEqual(c.k, 1.8171205928, places=9)  # from the saved W_max = 8

    def test_repeated_timeouts_keep_first_wmax_and_ssthresh(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_timeout(T0 + 0.5)
        c.on_timeout(T0 + 1.5)
        c.on_timeout(T0 + 3.5)
        self.assertEqual(c.w_max(), 8 * MSS)
        self.assertEqual(c.ssthresh(), 5 * MSS)
        self.assertEqual(c.cwnd(), MSS)

    def test_stale_acks_and_losses_after_timeout_are_ignored(self):
        c = ctrl()
        to_ca_at_8(c)
        for pn in range(1, 15):
            c.on_packet_sent(pn, MSS, T0)
        c.on_timeout(T0 + 0.5)
        c.on_loss([P(10)], T0 + 0.6)  # packet sent before the timeout
        c.on_ack([P(11)], RttStats(0.1), T0 + 0.6)
        self.assertEqual(c.cwnd(), MSS)
        self.assertEqual(c.w_max(), 8 * MSS)


class PersistentCongestionTests(unittest.TestCase):
    def test_cwnd_two_mss_and_slow_start(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_persistent_congestion()
        self.assertEqual(c.cwnd(), 2 * MSS)
        self.assertEqual(c.w_max(), 8 * MSS)
        self.assertEqual(c.ssthresh(), 5 * MSS)
        self.assertTrue(c.in_slow_start)

    def test_small_window_still_has_slow_start_room(self):
        c = ctrl()  # cwnd = 2 packets already
        c.on_persistent_congestion()
        self.assertEqual(c.cwnd(), 2 * MSS)
        self.assertEqual(c.ssthresh(), 3 * MSS)  # min window + 1 MSS
        self.assertTrue(c.in_slow_start)

    def test_differs_from_timeout(self):
        a, b = ctrl(), ctrl()
        to_ca_at_8(a)
        to_ca_at_8(b)
        a.on_timeout(T0 + 1)
        b.on_persistent_congestion()
        self.assertEqual(a.cwnd(), MSS)
        self.assertEqual(b.cwnd(), 2 * MSS)

    def test_design_doc_preset_persistent_congestion(self):
        c = ctrl(CubicConfig.design_doc())  # cwnd 10 packets, ssthresh inf
        c.on_persistent_congestion()
        self.assertEqual(c.cwnd(), 2 * MSS)
        self.assertEqual(c.ssthresh(), 7 * MSS * 1.0)  # 0.7 * 10 packets, no flooring
        self.assertTrue(c.in_slow_start)


class PacingRateTests(unittest.TestCase):
    def test_defaults_to_333ms_before_first_sample(self):
        c = ctrl()
        self.assertAlmostEqual(c.pacing_rate(), 2 * 2400 / 0.333, places=6)

    def test_slow_start_gain_2(self):
        c = ctrl()
        c.on_ack([], RttStats(0.1), T0)
        self.assertAlmostEqual(c.pacing_rate(), 2 * 2400 / 0.1, places=6)  # 48 000 B/s

    def test_congestion_avoidance_gain_1_2(self):
        c = ctrl()
        to_ca_at_8(c)  # srtt 0.1, cwnd 9600
        self.assertAlmostEqual(
            c.pacing_rate(), 1.2 * 9600 / 0.1, places=6
        )  # 115 200 B/s

    def test_accepts_plain_float_rtt(self):
        c = ctrl()
        c.on_ack([], 0.2, T0)
        self.assertAlmostEqual(c.pacing_rate(), 2 * 2400 / 0.2, places=6)

    def test_invalid_rtt_values_never_break_rate(self):
        for bad in (0, 0.0, -1.0, math.nan, math.inf, -math.inf, None, "x"):
            c = ctrl()
            c.on_ack([], RttStats(0.1), T0)
            c.on_ack([P(1)], RttStats(bad), T0)  # sample ignored, srtt stays 0.1
            rate = c.pacing_rate()
            self.assertTrue(math.isfinite(rate) and rate > 0, bad)
            self.assertAlmostEqual(rate, 2 * 3600 / 0.1, places=6, msg=repr(bad))

    def test_tiny_rtt_is_finite(self):
        c = ctrl()
        c.on_ack([], 1e-300, T0)
        self.assertTrue(math.isfinite(c.pacing_rate()))

    def test_rate_follows_window_after_loss(self):
        c = ctrl()
        to_ca_at_8(c)
        c.on_packet_sent(9, MSS, T0 + 0.2)
        c.on_loss([P(9)], T0 + 0.3)
        self.assertAlmostEqual(c.pacing_rate(), 1.2 * 6000 / 0.1, places=6)


class RobustnessTests(unittest.TestCase):
    def test_bogus_packet_sizes_ignored(self):
        c = ctrl()
        c.on_ack([P(1, 0), P(2, -5), P(3, math.nan), P(4, None)], RttStats(), T0)
        self.assertEqual(c.cwnd(), 2 * MSS)

    def test_window_capped_without_ssthresh(self):
        c = ctrl(CubicConfig(initial_ssthresh_packets=None))
        c.on_ack([P(1, 10**12)], RttStats(), T0)
        self.assertEqual(c.cwnd(), c.config.max_cwnd_bytes)
        self.assertTrue(math.isfinite(c.pacing_rate()))

    def test_window_never_below_one_mss(self):
        c = ctrl()
        for i in range(5):
            c.on_timeout(T0 + i)
            c.on_persistent_congestion()
            c.on_timeout(T0 + i + 0.5)
        self.assertGreaterEqual(c.cwnd(), MSS)

    def test_longer_event_sequence(self):
        """ACKs, fast loss, recovery, timeout, recovery: invariants hold throughout."""
        c = ctrl()
        now = T0
        for rnd in range(60):
            now += 0.05
            pn = rnd + 1
            c.on_packet_sent(pn, MSS, now)
            if rnd == 20:
                c.on_loss([P(pn)], now)
            elif rnd == 40:
                c.on_timeout(now)
            else:
                c.on_ack([P(pn)], RttStats(0.05), now)
            self.assertTrue(MSS <= c.cwnd() <= c.config.max_cwnd_bytes)
            self.assertTrue(math.isfinite(c.pacing_rate()))
            self.assertFalse(math.isnan(c.ssthresh()))


if __name__ == "__main__":
    unittest.main()
