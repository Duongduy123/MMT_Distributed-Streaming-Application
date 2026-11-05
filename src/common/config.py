"""Configuration models and validation for both process roles.

Source: architecture doc sections 2-3 and 15; review items 4 and 8.
Status: IMPLEMENTED (validation only -- no sockets are opened here).

Rules:
* The client must receive the server IP explicitly (no hard-coded LAN IP).
* The client destination must be a usable unicast IPv4 address: ``0.0.0.0`` (a wildcard *bind*
  address), broadcast and multicast are rejected; loopback is allowed for single-machine testing.
* Ports are integers in 1..65535.
* Two TCP listeners of the same process may not share a port on overlapping bind addresses.
  UDP 9000 lives in a separate (UDP) port namespace and never collides with TCP ports.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

from src.common import constants as C
from src.common.exceptions import ConfigError

WILDCARD_BIND = "0.0.0.0"


def validate_port(value: Any, name: str) -> int:
    """Return ``value`` as a valid port number or raise :class:`ConfigError`."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ConfigError(f"{name}: port must be an integer, got {value!r}")
    if isinstance(value, str):
        if not value.strip().isdigit():
            raise ConfigError(f"{name}: port must be an integer, got {value!r}")
        value = int(value.strip())
    if not isinstance(value, int):
        raise ConfigError(f"{name}: port must be an integer, got {value!r}")
    if not C.MIN_PORT <= value <= C.MAX_PORT:
        raise ConfigError(f"{name}: port {value} outside {C.MIN_PORT}..{C.MAX_PORT}")
    return value


def validate_bind_address(value: str, name: str) -> str:
    """A local bind address: any syntactically valid IPv4 (``0.0.0.0`` allowed)."""
    try:
        return str(ipaddress.IPv4Address(value))
    except (ipaddress.AddressValueError, ValueError):
        raise ConfigError(f"{name}: {value!r} is not a valid IPv4 address") from None


def validate_destination_address(value: str, name: str) -> str:
    """A remote destination: valid unicast IPv4; rejects wildcard, broadcast, multicast."""
    try:
        addr = ipaddress.IPv4Address(value)
    except (ipaddress.AddressValueError, ValueError):
        raise ConfigError(f"{name}: {value!r} is not a valid IPv4 address") from None
    if addr.is_unspecified:
        raise ConfigError(
            f"{name}: 0.0.0.0 is a wildcard bind address, not a destination; "
            "use the server's LAN IPv4 (or 127.0.0.1 for local testing)"
        )
    if addr == ipaddress.IPv4Address("255.255.255.255") or addr.is_multicast:
        raise ConfigError(f"{name}: {value} is a broadcast/multicast address, not a server")
    return str(addr)


def validate_log_level(value: str) -> str:
    """Return the upper-cased log level or raise :class:`ConfigError`."""
    level = str(value).upper()
    if level not in C.LOG_LEVELS:
        raise ConfigError(f"log level must be one of {', '.join(C.LOG_LEVELS)}, got {value!r}")
    return level


def binds_overlap(a: str, b: str) -> bool:
    """True if two IPv4 bind addresses could conflict for the same TCP port."""
    return a == b or a == WILDCARD_BIND or b == WILDCARD_BIND


@dataclass(frozen=True)
class ServerConfig:
    """Configuration of the server process (Machine A)."""

    network_bind: str = C.DEFAULT_SERVER_NETWORK_BIND  # control TCP + UDP
    ui_bind: str = C.DEFAULT_SERVER_UI_BIND            # dashboard
    ui_port: int = C.SERVER_UI_PORT
    tcp_port: int = C.CONTROL_TCP_PORT
    udp_port: int = C.UDP_TRANSPORT_PORT
    log_level: str = C.DEFAULT_LOG_LEVEL

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "network_bind", validate_bind_address(self.network_bind, "--bind"))
        set_(self, "ui_bind", validate_bind_address(self.ui_bind, "--ui-bind"))
        set_(self, "ui_port", validate_port(self.ui_port, "--ui-port"))
        set_(self, "tcp_port", validate_port(self.tcp_port, "--tcp-port"))
        set_(self, "udp_port", validate_port(self.udp_port, "--udp-port"))
        set_(self, "log_level", validate_log_level(self.log_level))
        if self.ui_port == self.tcp_port and binds_overlap(self.ui_bind, self.network_bind):
            raise ConfigError(
                f"TCP port collision: dashboard {self.ui_bind}:{self.ui_port} overlaps control "
                f"listener {self.network_bind}:{self.tcp_port}; choose different ports"
            )

    @classmethod
    def from_args(cls, ns: Any) -> ServerConfig:
        """Build from an ``argparse.Namespace`` produced by ``src.server.config``."""
        return cls(
            network_bind=ns.bind,
            ui_bind=ns.ui_bind,
            ui_port=ns.ui_port,
            tcp_port=ns.tcp_port,
            udp_port=ns.udp_port,
            log_level=ns.log_level,
        )


@dataclass(frozen=True)
class ClientConfig:
    """Configuration of one client process (Machine B, C, ...).

    ``tcp_port`` / ``udp_port`` are the SERVER's destination ports. The client's own UDP source
    port is ephemeral (OS-assigned); it is deliberately not configurable here.
    """

    server_host: str
    tcp_port: int = C.CONTROL_TCP_PORT
    udp_port: int = C.UDP_TRANSPORT_PORT
    ui_port: int = C.CLIENT_UI_PORT
    ui_bind: str = C.DEFAULT_CLIENT_UI_BIND
    log_level: str = C.DEFAULT_LOG_LEVEL

    def __post_init__(self) -> None:
        if not self.server_host:
            raise ConfigError("--server is required (the server machine's LAN IPv4)")
        set_ = object.__setattr__
        set_(self, "server_host", validate_destination_address(self.server_host, "--server"))
        set_(self, "tcp_port", validate_port(self.tcp_port, "--tcp-port"))
        set_(self, "udp_port", validate_port(self.udp_port, "--udp-port"))
        set_(self, "ui_port", validate_port(self.ui_port, "--ui-port"))
        set_(self, "ui_bind", validate_bind_address(self.ui_bind, "--ui-bind"))
        set_(self, "log_level", validate_log_level(self.log_level))

    @classmethod
    def from_args(cls, ns: Any) -> ClientConfig:
        """Build from an ``argparse.Namespace`` produced by ``src.client.config``."""
        return cls(
            server_host=ns.server,
            tcp_port=ns.tcp_port,
            udp_port=ns.udp_port,
            ui_port=ns.ui_port,
            ui_bind=ns.ui_bind,
            log_level=ns.log_level,
        )
