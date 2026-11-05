"""Ordered start, reverse rollback on partial failure, idempotent stop, honest scaffold exit."""

from __future__ import annotations

import logging
import threading
import unittest
from unittest import mock

from src.common import constants as C
from src.common.config import ClientConfig, ServerConfig
from src.common.exceptions import ServiceStartError
from src.common.lifecycle import ServiceGroup


class FakeService:
    def __init__(self, name: str, log: list[str], fail: bool = False) -> None:
        self.name = name
        self._log = log
        self._fail = fail

    def start(self) -> None:
        self._log.append(f"start:{self.name}")
        if self._fail:
            raise OSError("bind failed")

    def stop(self) -> None:
        self._log.append(f"stop:{self.name}")


class ServiceGroupTests(unittest.TestCase):
    def test_partial_failure_rolls_back_in_reverse(self) -> None:
        log: list[str] = []
        group = ServiceGroup([FakeService("a", log), FakeService("b", log), FakeService("c", log, fail=True)])
        with self.assertRaises(ServiceStartError) as ctx:
            group.start_all()
        self.assertEqual(ctx.exception.service_name, "c")
        self.assertEqual(log, ["start:a", "start:b", "start:c", "stop:c", "stop:b", "stop:a"])
        self.assertEqual(group.started, [])

    def test_stop_all_is_idempotent(self) -> None:
        log: list[str] = []
        group = ServiceGroup([FakeService("a", log), FakeService("b", log)])
        group.start_all()
        group.stop_all()
        group.stop_all()
        self.assertEqual(log, ["start:a", "start:b", "stop:b", "stop:a"])


def _forbid(*_a, **_k):
    raise AssertionError("no socket/thread may be created in the scaffold")


class ScaffoldRunTests(unittest.TestCase):
    """run() must report 'not implemented' honestly instead of pretending to serve."""

    def test_server_run_returns_not_implemented(self) -> None:
        from src.server.application import ServerApplication

        with mock.patch("socket.socket", side_effect=_forbid), \
             mock.patch.object(threading.Thread, "start", _forbid), \
             self.assertLogs("src.server.application", logging.ERROR) as logs:
            code = ServerApplication(ServerConfig()).run()
        self.assertEqual(code, C.EXIT_NOT_IMPLEMENTED)
        self.assertIn("scaffold only", "\n".join(logs.output))

    def test_client_run_returns_not_implemented(self) -> None:
        from src.client.application import ClientApplication

        with mock.patch("socket.socket", side_effect=_forbid), \
             mock.patch.object(threading.Thread, "start", _forbid), \
             self.assertLogs("src.client.application", logging.ERROR):
            code = ClientApplication(ClientConfig(server_host="127.0.0.1")).run()
        self.assertEqual(code, C.EXIT_NOT_IMPLEMENTED)

    def test_server_start_order(self) -> None:
        from src.server.application import ServerApplication

        names = [s.name for s in ServerApplication(ServerConfig()).build_services()]
        self.assertEqual(names, ["control-plane", "udp-transport", "server-dashboard"])


if __name__ == "__main__":
    unittest.main()
