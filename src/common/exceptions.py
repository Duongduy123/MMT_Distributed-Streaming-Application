"""Project exception hierarchy. Status: SCAFFOLD."""

from __future__ import annotations


class AppError(Exception):
    """Base class for all project-specific errors."""


class ConfigError(AppError):
    """Invalid configuration or command-line argument."""


class ServiceStartError(AppError):
    """A service failed to start; carries the service name for partial-startup rollback."""

    def __init__(self, service_name: str, cause: BaseException) -> None:
        super().__init__(f"service {service_name!r} failed to start: {cause}")
        self.service_name = service_name
        self.cause = cause


class ProtocolError(AppError):
    """Malformed or unexpected protocol data (HTTP control plane or UDP transport)."""
