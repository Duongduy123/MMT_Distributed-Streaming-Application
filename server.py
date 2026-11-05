"""Server process entry point (Machine A). The ONLY server executable.

Usage (planned; see README "Current status" for what works today):
    python server.py [--bind 0.0.0.0] [--ui-bind 127.0.0.1] [--ui-port 3000]
                     [--tcp-port 8080] [--udp-port 9000] [--log-level INFO]

Exit codes: 0 ok, 1 startup failure, 2 scaffold (service not implemented), 64 invalid config.
"""

from __future__ import annotations

import sys

from src.common import constants as C
from src.common.config import ServerConfig
from src.common.exceptions import ConfigError
from src.common.logging_config import configure_logging
from src.server.application import ServerApplication
from src.server.config import build_arg_parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, validate configuration, run the server process."""
    args = build_arg_parser().parse_args(argv)
    try:
        config = ServerConfig.from_args(args)
    except ConfigError as exc:
        print(f"server.py: error: {exc}", file=sys.stderr)
        return C.EXIT_CONFIG_ERROR
    configure_logging(config.log_level)
    app = ServerApplication(config)
    try:
        return app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    sys.exit(main())
