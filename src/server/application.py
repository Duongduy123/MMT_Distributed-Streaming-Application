"""Server process lifecycle owner. Status: SCAFFOLD (orchestration real, services are stubs).

Owns and wires:
    session manager + presence manager + authentication   (shared state, src.server.backend)
    ControlServer       TCP  <network_bind>:8080   HTTP/1.1 control plane (D1)
    UdpTransportServer  UDP  <network_bind>:9000   transport + relay
    DashboardServer     TCP  <ui_bind>:3000        server dashboard (127.0.0.1 by default)

Start order: control -> UDP -> dashboard. On any failure the already-started services are
stopped in reverse order (``ServiceGroup``) and the process exits non-zero. In the scaffolding
phase every service's ``start()`` raises ``NotImplementedError``; ``run()`` reports that
honestly and returns ``EXIT_NOT_IMPLEMENTED`` -- it never pretends to be running.
"""

from __future__ import annotations

import logging
import threading

from src.common import constants as C
from src.common.config import ServerConfig
from src.common.exceptions import ServiceStartError
from src.common.lifecycle import Service, ServiceGroup
from src.server.backend.authentication import Authenticator
from src.server.backend.control_server import ControlServer
from src.server.backend.presence_manager import PresenceManager
from src.server.backend.session_manager import SessionManager
from src.server.frontend.http_server import DashboardServer
from src.server.udp.udp_server import UdpTransportServer

log = logging.getLogger(__name__)


class ServerApplication:
    """Composes the server's services. Constructing it opens no sockets."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.sessions = SessionManager()
        self.presence = PresenceManager()
        self.auth = Authenticator()
        self._shutdown = threading.Event()
        self._group = ServiceGroup(self.build_services())

    def build_services(self) -> list[Service]:
        """Services in start order."""
        cfg = self.config
        return [
            ControlServer(cfg.network_bind, cfg.tcp_port, self.auth, self.sessions, self.presence),
            UdpTransportServer(cfg.network_bind, cfg.udp_port, self.sessions),
            DashboardServer(cfg.ui_bind, cfg.ui_port),
        ]

    def run(self) -> int:
        """Start all services and block until shutdown. Returns a process exit code."""
        cfg = self.config
        log.info(
            "server process: control TCP %s:%d, UDP %s:%d, dashboard TCP %s:%d",
            cfg.network_bind, cfg.tcp_port, cfg.network_bind, cfg.udp_port, cfg.ui_bind, cfg.ui_port,
        )
        try:
            self._group.start_all()
        except ServiceStartError as exc:
            if isinstance(exc.cause, NotImplementedError):
                log.error(
                    "scaffold only -- service %r is not implemented yet (%s). "
                    "No listener is running.", exc.service_name, exc.cause,
                )
                return C.EXIT_NOT_IMPLEMENTED
            log.error("startup failed: %s", exc)
            return C.EXIT_STARTUP_FAILURE
        try:
            # Short waits keep Ctrl+C responsive on Windows; this is not a busy loop.
            while not self._shutdown.wait(0.5):
                pass
        except KeyboardInterrupt:
            log.info("interrupted")
        finally:
            self.shutdown()
        return C.EXIT_OK

    def shutdown(self) -> None:
        """Stop all started services in reverse order. Idempotent, callable from any thread."""
        self._shutdown.set()
        self._group.stop_all()
