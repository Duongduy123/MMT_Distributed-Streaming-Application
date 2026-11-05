"""Print this machine's network addresses for setting up server/client runs.

Distinguishes WILDCARD BIND addresses (what a server listens on) from DESTINATION addresses
(what a client must type after ``--server``). Sends no packets: the "primary route" probe only
calls ``connect()`` on a UDP socket, which selects a route without transmitting anything.
"""

from __future__ import annotations

import ipaddress
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common import constants as C  # noqa: E402

# Any non-local address works for route selection; nothing is sent to it.
_ROUTE_PROBE = ("10.254.254.254", 1)


def _label(ip: str) -> str:
    addr = ipaddress.IPv4Address(ip)
    if addr.is_loopback:
        return "loopback -- same machine only"
    if addr.is_link_local:
        return "link-local (169.254.x.x) -- usually no DHCP; not a good destination"
    if addr.is_private:
        return "private LAN address -- candidate for --server"
    return "non-private address"


def _primary_route_ip() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(_ROUTE_PROBE)
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def main() -> int:
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}\n")

    print("Bind addresses used by the server (wildcard; NOT a destination):")
    print(f"  control TCP {C.DEFAULT_SERVER_NETWORK_BIND}:{C.CONTROL_TCP_PORT}")
    print(f"  UDP         {C.DEFAULT_SERVER_NETWORK_BIND}:{C.UDP_TRANSPORT_PORT}")
    print(f"  dashboard   {C.DEFAULT_SERVER_UI_BIND}:{C.SERVER_UI_PORT}  (local only unless --ui-bind is changed)\n")

    candidates: set[str] = set()
    try:
        candidates.update(socket.gethostbyname_ex(hostname)[2])
    except OSError:
        pass
    primary = _primary_route_ip()
    if primary:
        candidates.add(primary)

    print("Candidate IPv4 addresses of THIS machine (use one as the client's --server):")
    if not candidates:
        print("  none found -- check the network adapter")
    for ip in sorted(candidates, key=ipaddress.IPv4Address):
        mark = "  <- primary route" if ip == primary else ""
        print(f"  {ip:<16} {_label(ip)}{mark}")
    print(
        "\nNote: virtual adapters (WSL, Docker, VirtualBox, VPN) may appear above and cannot be\n"
        "excluded reliably. Confirm the Wi-Fi/Ethernet adapter's IPv4 with 'ipconfig' (Windows)\n"
        "or 'ip addr' (Linux) and make sure the firewall allows TCP 8080 and UDP 9000."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
