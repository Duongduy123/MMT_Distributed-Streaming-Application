"""Importing modules (and constructing the applications) must not open sockets or start threads."""

from __future__ import annotations

import importlib
import pkgutil
import sys
import threading
import unittest
from unittest import mock

import src
from src.common.config import ClientConfig, ServerConfig


def _all_src_modules() -> list[str]:
    names = ["src"]
    for info in pkgutil.walk_packages(src.__path__, prefix="src."):
        names.append(info.name)
    return sorted(names)


class _Forbidden(AssertionError):
    pass


def _forbid(*_args, **_kwargs):
    raise _Forbidden("socket/thread created during import or construction")


class ImportSafetyTests(unittest.TestCase):
    def test_every_module_imports_without_side_effects(self) -> None:
        names = _all_src_modules()
        self.assertGreater(len(names), 30)
        saved = {n: m for n, m in sys.modules.items() if n == "src" or n.startswith("src.")}
        for n in saved:
            del sys.modules[n]
        try:
            with mock.patch("socket.socket", side_effect=_forbid), \
                 mock.patch.object(threading.Thread, "start", _forbid):
                for name in names:
                    with self.subTest(module=name):
                        importlib.import_module(name)  # constraint-scan: allow-dynamic-import
        finally:
            for n in [n for n in sys.modules if n == "src" or n.startswith("src.")]:
                del sys.modules[n]
            sys.modules.update(saved)

    def test_constructing_applications_opens_nothing(self) -> None:
        from src.client.application import ClientApplication
        from src.server.application import ServerApplication

        with mock.patch("socket.socket", side_effect=_forbid), \
             mock.patch.object(threading.Thread, "start", _forbid):
            ServerApplication(ServerConfig())
            ClientApplication(ClientConfig(server_host="127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
