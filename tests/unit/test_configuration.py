"""Configuration and CLI validation (no sockets are opened)."""

from __future__ import annotations

import contextlib
import io
import unittest

import client
import server
from src.client.config import build_arg_parser as client_parser
from src.common import constants as C
from src.common.config import ClientConfig, ServerConfig
from src.common.exceptions import ConfigError


class ServerConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        cfg = ServerConfig()
        self.assertEqual(cfg.network_bind, "0.0.0.0")
        self.assertEqual(cfg.ui_bind, "127.0.0.1")  # dashboard not exposed by default
        self.assertEqual((cfg.ui_port, cfg.tcp_port, cfg.udp_port), (3000, 8080, 9000))

    def test_default_constants_are_separate(self) -> None:
        self.assertEqual(C.DEFAULT_SERVER_NETWORK_BIND, "0.0.0.0")
        self.assertEqual(C.DEFAULT_SERVER_UI_BIND, "127.0.0.1")
        self.assertEqual(C.DEFAULT_CLIENT_UI_BIND, "127.0.0.1")

    def test_invalid_ports_rejected(self) -> None:
        for bad in (0, 70000, -1, "abc", "", True, 80.5, None):
            with self.subTest(port=bad), self.assertRaises(ConfigError):
                ServerConfig(tcp_port=bad)

    def test_string_port_from_cli_accepted(self) -> None:
        self.assertEqual(ServerConfig(udp_port="9100").udp_port, 9100)

    def test_invalid_bind_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            ServerConfig(network_bind="not-an-ip")

    def test_tcp_collision_on_overlapping_binds(self) -> None:
        with self.assertRaises(ConfigError):
            ServerConfig(ui_port=8080, ui_bind="0.0.0.0")
        with self.assertRaises(ConfigError):  # wildcard network bind overlaps loopback ui bind
            ServerConfig(ui_port=8080)

    def test_same_port_on_disjoint_binds_allowed(self) -> None:
        cfg = ServerConfig(network_bind="192.168.1.10", ui_bind="127.0.0.1", ui_port=8080)
        self.assertEqual(cfg.ui_port, cfg.tcp_port)

    def test_udp_port_equal_to_tcp_port_is_not_a_collision(self) -> None:
        self.assertEqual(ServerConfig(udp_port=8080).udp_port, 8080)

    def test_invalid_log_level(self) -> None:
        with self.assertRaises(ConfigError):
            ServerConfig(log_level="LOUD")


class ClientConfigTests(unittest.TestCase):
    def test_valid(self) -> None:
        cfg = ClientConfig(server_host="192.168.1.10")
        self.assertEqual(cfg.ui_bind, "127.0.0.1")
        self.assertEqual((cfg.tcp_port, cfg.udp_port, cfg.ui_port), (8080, 9000, 3000))

    def test_loopback_allowed_for_local_testing(self) -> None:
        self.assertEqual(ClientConfig(server_host="127.0.0.1").server_host, "127.0.0.1")

    def test_bad_destinations_rejected(self) -> None:
        for bad in ("0.0.0.0", "255.255.255.255", "224.0.0.1", "999.1.1.1", "abc", ""):
            with self.subTest(server=bad), self.assertRaises(ConfigError):
                ClientConfig(server_host=bad)

    def test_bad_ports_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            ClientConfig(server_host="10.0.0.1", tcp_port=70000)
        with self.assertRaises(ConfigError):
            ClientConfig(server_host="10.0.0.1", ui_port=0)


class CliTests(unittest.TestCase):
    def _run(self, main, argv: list[str]) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_help_exits_zero(self) -> None:
        self.assertEqual(self._run(server.main, ["--help"])[0], 0)
        self.assertEqual(self._run(client.main, ["--help"])[0], 0)

    def test_client_requires_server(self) -> None:
        code, err = self._run(client.main, [])
        self.assertEqual(code, 2)  # argparse usage error
        self.assertIn("--server", err)

    def test_client_server_ip_parsing(self) -> None:
        ns = client_parser().parse_args(["--server", "192.168.1.10", "--ui-port", "3001"])
        cfg = ClientConfig.from_args(ns)
        self.assertEqual((cfg.server_host, cfg.ui_port), ("192.168.1.10", 3001))

    def test_invalid_config_exit_code(self) -> None:
        code, err = self._run(client.main, ["--server", "0.0.0.0"])
        self.assertEqual(code, C.EXIT_CONFIG_ERROR)
        self.assertIn("wildcard", err)
        code, _ = self._run(server.main, ["--tcp-port", "70000"])
        self.assertEqual(code, C.EXIT_CONFIG_ERROR)


if __name__ == "__main__":
    unittest.main()
