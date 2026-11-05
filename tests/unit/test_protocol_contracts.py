"""Interface contracts: modules import, stubs are explicit, enums are layer-separated.

These tests do NOT claim to verify any protocol, reliability or congestion behaviour.
"""

from __future__ import annotations

import unittest

from src.common.protocol import packet_header
from src.common.protocol.application_messages import ApplicationMessageType
from src.common.protocol.control_messages import ControlOperation
from src.common.protocol.transport_frames import TransportFrameKind
from src.transport.congestion_control import CubicController
from src.transport.contracts import CongestionController
from src.transport.flow_control import ReceiverFlowWindow, SenderFlowWindow
from src.transport.reliability import ReliabilityReceiver, ReliabilitySender
from src.transport.timer_host import ThreadTimerHost


class EnumSeparationTests(unittest.TestCase):
    def test_layers_do_not_share_member_names(self) -> None:
        app = set(ApplicationMessageType.__members__)
        ctl = set(ControlOperation.__members__)
        trn = set(TransportFrameKind.__members__)
        self.assertEqual(app & trn, set())
        self.assertEqual(app & ctl, set())
        self.assertEqual(ctl & trn, set())

    def test_expected_names_present(self) -> None:
        self.assertTrue({"AUTH", "MSG", "FILE"} <= set(ApplicationMessageType.__members__))
        self.assertTrue({"DATA", "ACK", "WND_PROBE"} <= set(TransportFrameKind.__members__))

    def test_no_wire_format_defined(self) -> None:
        self.assertIn("GATED ON D14", packet_header.HEADER_FORMAT_STATUS)


class TransportContractTests(unittest.TestCase):
    def test_existing_cubic_satisfies_congestion_controller(self) -> None:
        self.assertIsInstance(CubicController(), CongestionController)

    def test_thread_timer_host_matches_paced_sender_timer_interface(self) -> None:
        host = ThreadTimerHost()
        for member in ("time", "call_at"):  # exactly what PacedSender uses (TimerHostLike)
            self.assertTrue(callable(getattr(host, member)))
        self.assertTrue(callable(host.post))
        self.assertIsInstance(host.time(), float)

    def test_stubs_raise_not_implemented(self) -> None:
        cases = [
            lambda: ThreadTimerHost().call_at(0.0, lambda: None),
            lambda: ThreadTimerHost().start(),
            lambda: ReliabilitySender().on_rto_timer(0.0),
            lambda: ReliabilityReceiver().build_feedback(0.0),
            lambda: SenderFlowWindow().allows(1, 0),
            lambda: ReceiverFlowWindow().advertised_window(),
        ]
        for i, call in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(NotImplementedError):
                call()


if __name__ == "__main__":
    unittest.main()
