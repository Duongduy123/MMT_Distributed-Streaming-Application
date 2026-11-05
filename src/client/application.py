"""Client process lifecycle owner. Status: SCAFFOLD (orchestration real, services are stubs).

Owns and wires:
    UdpClient          UDP  ephemeral local port -> SERVER:9000   (transport data plane)
    TcpControlClient   TCP  ephemeral local port -> SERVER:8080   (HTTP/1.1 control plane, D1)
    ClientUiServer     TCP  <ui_bind>:3000 (127.0.0.1)            static UI + /api/* on ONE listener
    EventHub                                                       Python -> browser events (D2)

Start order: UDP -> TCP -> UI (the UDP socket exists before the control plane registers its
endpoint). Partial failures roll back in reverse order. In this phase ``run()`` reports the
unimplemented service and returns ``EXIT_NOT_IMPLEMENTED``.
"""

from __future__ import annotations

import logging
import threading

from src.common import constants as C
from src.common.config import ClientConfig
from src.common.exceptions import ServiceStartError
from src.common.lifecycle import Service, ServiceGroup
from src.client.frontend.event_hub import EventHub
from src.client.frontend.http_server import ClientUiServer
from src.client.frontend.local_api import LocalApi
from src.client.tcp.tcp_client import TcpControlClient
from src.client.udp.udp_client import UdpClient

log = logging.getLogger(__name__)


class ClientApplication:
    """Composes the client's services. Constructing it opens no sockets."""

    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self.events = EventHub()
        self.udp = UdpClient(config.server_host, config.udp_port)
        self.tcp = TcpControlClient(config.server_host, config.tcp_port, self.events)
        self.api = LocalApi(self.tcp, self.udp, self.events)
        self._shutdown = threading.Event()
        self._group = ServiceGroup(self.build_services())

    def build_services(self) -> list[Service]:
        """Services in start order."""
        return [self.udp, self.tcp, ClientUiServer(self.config.ui_bind, self.config.ui_port, self.api)]

    def run(self) -> int:
        """Start all services and block until shutdown. Returns a process exit code."""
        cfg = self.config
        log.info(
            "client process: server %s (TCP %d, UDP %d), local UI http://%s:%d/",
            cfg.server_host, cfg.tcp_port, cfg.udp_port, cfg.ui_bind, cfg.ui_port,
        )
        try:
            self._group.start_all()
        except ServiceStartError as exc:
            if isinstance(exc.cause, NotImplementedError):
                log.error(
                    "scaffold only -- service %r is not implemented yet (%s). "
                    "Nothing is connected.", exc.service_name, exc.cause,
                )
                return C.EXIT_NOT_IMPLEMENTED
            log.error("startup failed: %s", exc)
            return C.EXIT_STARTUP_FAILURE
        try:
            while not self._shutdown.wait(0.5):  # keeps Ctrl+C responsive on Windows
                pass
        except KeyboardInterrupt:
            log.info("interrupted")
        finally:
            self.shutdown()
        return C.EXIT_OK

    def shutdown(self) -> None:
        """Stop all started services in reverse order. Idempotent."""
        self._shutdown.set()
        self._group.stop_all()
