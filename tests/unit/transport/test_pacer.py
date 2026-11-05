import math
import unittest

from src.transport.pacer import Pacer

MSS = 1200
CAP = 10 * MSS
T0 = 50.0


def drained(rate=12000.0, now=T0, **kw):
    p = Pacer(rate, now, **kw)
    assert p.try_consume(CAP, now)
    return p


class InitTests(unittest.TestCase):
    def test_capacity_is_ten_mss_and_starts_full(self):
        p = Pacer(12000.0, T0)
        self.assertEqual(p.capacity, 12000)
        self.assertEqual(p.tokens(T0), 12000)
        self.assertEqual(p.rate, 12000.0)

    def test_rejects_bad_geometry(self):
        with self.assertRaises(ValueError):
            Pacer(1.0, T0, mss=0)
        with self.assertRaises(ValueError):
            Pacer(1.0, T0, capacity_packets=0)


class RefillTests(unittest.TestCase):
    def test_refill_after_known_interval(self):
        p = drained(rate=12000.0)
        self.assertAlmostEqual(p.tokens(T0 + 0.25), 3000.0, places=6)
        self.assertAlmostEqual(p.tokens(T0 + 0.5), 6000.0, places=6)

    def test_refill_is_capped(self):
        p = drained()
        self.assertEqual(p.tokens(T0 + 1000), CAP)

    def test_clock_going_backwards_earns_nothing(self):
        p = drained()
        p.tokens(T0 + 0.5)
        before = p.tokens(T0 + 0.5)
        self.assertEqual(p.tokens(T0 + 0.1), before)
        self.assertGreaterEqual(p.tokens(T0 + 0.1), 0)

    def test_non_finite_now_is_ignored(self):
        p = drained()
        self.assertEqual(p.tokens(math.nan), 0.0)


class ConsumeTests(unittest.TestCase):
    def test_blocked_when_insufficient_tokens(self):
        p = drained()
        now = T0 + 0.05  # 600 tokens
        self.assertFalse(p.can_send(MSS, now))
        self.assertFalse(p.try_consume(MSS, now))
        self.assertAlmostEqual(
            p.tokens(now), 600.0, places=6
        )  # failed attempt took nothing

    def test_consumes_exactly_packet_size(self):
        p = Pacer(12000.0, T0)
        self.assertTrue(p.try_consume(MSS, T0))
        self.assertAlmostEqual(p.tokens(T0), 10800.0, places=9)
        self.assertTrue(p.try_consume(500, T0))
        self.assertAlmostEqual(p.tokens(T0), 10300.0, places=9)

    def test_packet_exactly_matching_tokens_is_allowed(self):
        p = drained()
        self.assertTrue(p.try_consume(MSS, T0 + 0.1))  # 1200 tokens earned exactly
        self.assertAlmostEqual(p.tokens(T0 + 0.1), 0.0, places=6)

    def test_variable_sized_packets(self):
        p = Pacer(12000.0, T0)
        for size in (100, 1200, 37, 800, 1):
            self.assertTrue(p.try_consume(size, T0))
        self.assertAlmostEqual(p.tokens(T0), 12000 - 2138, places=9)

    def test_packet_larger_than_mss_but_within_bucket(self):
        p = Pacer(12000.0, T0)
        self.assertTrue(p.try_consume(2400, T0))
        self.assertAlmostEqual(p.tokens(T0), 9600.0, places=9)

    def test_packet_larger_than_bucket_cost_is_clamped(self):
        p = Pacer(12000.0, T0)
        self.assertTrue(p.can_send(50_000, T0))  # bucket full -> allowed once
        self.assertTrue(p.try_consume(50_000, T0))
        self.assertEqual(p.tokens(T0), 0.0)
        self.assertFalse(p.try_consume(50_000, T0 + 0.5))  # must wait for a full bucket
        self.assertAlmostEqual(p.time_until_ready(50_000, T0 + 0.5), 0.5, places=6)

    def test_zero_size_is_free_and_negative_is_error(self):
        p = Pacer(12000.0, T0)
        self.assertTrue(p.try_consume(0, T0))
        self.assertEqual(p.tokens(T0), CAP)
        for bad in (-1, math.nan, "x", None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                p.try_consume(bad, T0)

    def test_no_unlimited_burst_after_long_idle(self):
        p = Pacer(1_000_000.0, T0)
        sent = 0
        later = T0 + 3600
        while p.try_consume(MSS, later):
            sent += 1
            self.assertLess(sent, 1000)
        self.assertEqual(sent, 10)  # exactly the bucket, not an hour's worth


class RateTests(unittest.TestCase):
    def test_rate_change_settles_old_rate_first(self):
        p = drained(rate=1000.0)
        p.set_rate(4000.0, T0 + 1.0)  # 1 s at 1000 B/s = 1000 tokens already earned
        self.assertAlmostEqual(p.tokens(T0 + 1.0), 1000.0, places=6)
        self.assertAlmostEqual(p.tokens(T0 + 1.5), 3000.0, places=6)  # + 0.5 s at 4000

    def test_rate_decrease_keeps_earned_tokens(self):
        p = drained(rate=4000.0)
        p.set_rate(100.0, T0 + 1.0)
        self.assertAlmostEqual(p.tokens(T0 + 1.0), 4000.0, places=6)
        self.assertAlmostEqual(p.tokens(T0 + 2.0), 4100.0, places=6)

    def test_zero_rate_blocks_forever_without_timer_hint(self):
        p = drained(rate=0.0)
        self.assertFalse(p.try_consume(MSS, T0 + 100))
        self.assertIsNone(p.time_until_ready(MSS, T0 + 100))
        self.assertEqual(p.tokens(T0 + 100), 0.0)

    def test_invalid_rates_are_ignored(self):
        p = Pacer(5000.0, T0)
        for bad in (-1.0, math.nan, math.inf, -math.inf, None, "fast"):
            p.set_rate(bad, T0)
            self.assertEqual(p.rate, 5000.0, repr(bad))
        self.assertEqual(Pacer(math.nan, T0).rate, 0.0)
        self.assertEqual(Pacer(-5.0, T0).rate, 0.0)

    def test_extremely_small_rate(self):
        p = drained(rate=1e-3)
        wait = p.time_until_ready(MSS, T0)
        self.assertAlmostEqual(wait, 1.2e6, places=3)
        self.assertTrue(math.isfinite(wait))
        self.assertFalse(p.can_send(MSS, T0 + 60))

    def test_unrepresentably_small_rate_returns_none(self):
        p = drained(rate=5e-324)
        self.assertIsNone(p.time_until_ready(MSS, T0))

    def test_time_until_ready(self):
        p = drained(rate=12000.0)
        self.assertAlmostEqual(p.time_until_ready(MSS, T0), 0.1, places=9)
        self.assertAlmostEqual(p.time_until_ready(MSS, T0 + 0.04), 0.06, places=9)
        self.assertEqual(p.time_until_ready(MSS, T0 + 0.1), 0.0)
        self.assertEqual(p.time_until_ready(0, T0), 0.0)


class IndependenceTests(unittest.TestCase):
    def test_two_pacers_do_not_share_state(self):
        a, b = Pacer(12000.0, T0), Pacer(12000.0, T0)
        for _ in range(10):
            self.assertTrue(a.try_consume(MSS, T0))
        self.assertFalse(a.can_send(MSS, T0))
        self.assertTrue(b.can_send(MSS, T0))
        self.assertEqual(b.tokens(T0), CAP)
        a.set_rate(1.0, T0)
        self.assertEqual(b.rate, 12000.0)


if __name__ == "__main__":
    unittest.main()
