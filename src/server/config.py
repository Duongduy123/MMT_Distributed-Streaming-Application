"""Command-line interface of the server process. Status: IMPLEMENTED (parsing only)."""

from __future__ import annotations

import argparse

from src.common import constants as C


def build_arg_parser() -> argparse.ArgumentParser:
    """Arguments of ``python server.py``. Validation happens in ``ServerConfig``."""
    p = argparse.ArgumentParser(
        prog="server.py",
        description=(
            "Server process (Machine A): dashboard (TCP/HTTP), backend + TCP control plane "
            "(HTTP/1.1 over raw TCP), UDP transport/relay server."
        ),
    )
    p.add_argument(
        "--bind",
        default=C.DEFAULT_SERVER_NETWORK_BIND,
        help="bind address for the TCP control plane and UDP server (default: %(default)s)",
    )
    p.add_argument(
        "--ui-bind",
        default=C.DEFAULT_SERVER_UI_BIND,
        help="bind address for the dashboard (default: %(default)s = local only; "
        "use 0.0.0.0 to expose it to the LAN and allow it in the firewall)",
    )
    p.add_argument("--ui-port", default=C.SERVER_UI_PORT, help="dashboard TCP port (default: %(default)s)")
    p.add_argument("--tcp-port", default=C.CONTROL_TCP_PORT, help="control-plane TCP port (default: %(default)s)")
    p.add_argument("--udp-port", default=C.UDP_TRANSPORT_PORT, help="UDP transport port (default: %(default)s)")
    p.add_argument("--log-level", default=C.DEFAULT_LOG_LEVEL, help="DEBUG|INFO|WARNING|ERROR|CRITICAL")
    return p
