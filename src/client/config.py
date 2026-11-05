"""Command-line interface of the client process. Status: IMPLEMENTED (parsing only)."""

from __future__ import annotations

import argparse

from src.common import constants as C


def build_arg_parser() -> argparse.ArgumentParser:
    """Arguments of ``python client.py``. Validation happens in ``ClientConfig``."""
    p = argparse.ArgumentParser(
        prog="client.py",
        description=(
            "Client process: local browser UI + local API, TCP control client "
            "(HTTP/1.1 to SERVER:8080) and UDP transport client (to SERVER:9000)."
        ),
    )
    p.add_argument(
        "--server",
        required=True,
        help="server machine's LAN IPv4 (e.g. from 'ipconfig' on Machine A; 127.0.0.1 for local tests)",
    )
    p.add_argument("--tcp-port", default=C.CONTROL_TCP_PORT, help="server control-plane TCP port (default: %(default)s)")
    p.add_argument("--udp-port", default=C.UDP_TRANSPORT_PORT, help="server UDP transport port (default: %(default)s)")
    p.add_argument("--ui-port", default=C.CLIENT_UI_PORT, help="local UI TCP port (default: %(default)s)")
    p.add_argument(
        "--ui-bind",
        default=C.DEFAULT_CLIENT_UI_BIND,
        help="local UI bind address (default: %(default)s; not exposed to the LAN)",
    )
    p.add_argument("--log-level", default=C.DEFAULT_LOG_LEVEL, help="DEBUG|INFO|WARNING|ERROR|CRITICAL")
    return p
