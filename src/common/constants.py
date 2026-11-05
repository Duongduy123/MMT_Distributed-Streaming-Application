"""Finalized shared constants. This is the ONLY place default ports/binds are defined.

Source: MMT_Assignment_Architecture_and_Transport_Design.md sections 2-3, and review item 4
(separate network bind and dashboard bind; see docs/DECISIONS.md D12).

Status: SCAFFOLD (values agreed; nothing protocol-related is defined here until D14 is resolved).
"""

from __future__ import annotations

from typing import Final

# --- Ports (agreed in architecture doc section 2.1) ---------------------------------------------
SERVER_UI_PORT: Final[int] = 3000      # server dashboard (TCP/HTTP) on Machine A
CLIENT_UI_PORT: Final[int] = 3000      # local client UI (TCP/HTTP) on each client machine
CONTROL_TCP_PORT: Final[int] = 8080    # backend + TCP Control Plane (one listener, D1)
UDP_TRANSPORT_PORT: Final[int] = 9000  # centralized UDP transport/relay server

# --- Bind addresses (review item 4 / D12) --------------------------------------------------------
DEFAULT_SERVER_NETWORK_BIND: Final[str] = "0.0.0.0"  # control TCP 8080 + UDP 9000 only
DEFAULT_SERVER_UI_BIND: Final[str] = "127.0.0.1"     # dashboard is NOT exposed to the LAN by default
DEFAULT_CLIENT_UI_BIND: Final[str] = "127.0.0.1"     # client UI is local-only by default

# --- Validation bounds ---------------------------------------------------------------------------
MIN_PORT: Final[int] = 1
MAX_PORT: Final[int] = 65535

DEFAULT_LOG_LEVEL: Final[str] = "INFO"
LOG_LEVELS: Final[tuple[str, ...]] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

# --- Process exit codes ---------------------------------------------------------------------------
EXIT_OK: Final[int] = 0
EXIT_STARTUP_FAILURE: Final[int] = 1
EXIT_NOT_IMPLEMENTED: Final[int] = 2  # scaffolding phase: services exist only as interfaces
EXIT_CONFIG_ERROR: Final[int] = 64    # invalid arguments/configuration (BSD EX_USAGE)
