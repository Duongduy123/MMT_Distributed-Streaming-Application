"""Client process entry point (Machine B, C, ...). The ONLY client executable.

Usage (planned; see README "Current status" for what works today):
    python client.py --server <SERVER_LAN_IPv4> [--tcp-port 8080] [--udp-port 9000]
                     [--ui-port 3000] [--ui-bind 127.0.0.1] [--log-level INFO]

Exit codes: 0 ok, 1 startup failure, 2 scaffold (service not implemented), 64 invalid config.
"""

from __future__ import annotations

import sys

from src.client.application import ClientApplication
from src.client.config import build_arg_parser
from src.common import constants as C
from src.common.config import ClientConfig
from src.common.exceptions import ConfigError
from src.common.logging_config import configure_logging


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, validate configuration, run the client process."""
    args = build_arg_parser().parse_args(argv)
    try:
        config = ClientConfig.from_args(args)
    except ConfigError as exc:
        print(f"client.py: error: {exc}", file=sys.stderr)
        return C.EXIT_CONFIG_ERROR
    configure_logging(config.log_level)
    app = ClientApplication(config)
    try:
        return app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    sys.exit(main())
