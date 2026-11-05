"""Self-test of scripts/constraint_scan.py plus a scan of the real project."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import constraint_scan as cs  # noqa: E402


def tiers(source: str) -> list[tuple[str, str]]:
    return [(f.tier, f.module) for f in cs.scan_source(source)]


class DetectionTests(unittest.TestCase):
    def test_plain_and_aliased_imports(self) -> None:
        self.assertIn(("PROHIBITED", "asyncio"), tiers("import asyncio"))
        self.assertIn(("PROHIBITED", "flask"), tiers("import flask as f"))
        self.assertIn(("PROHIBITED", "http.server"), tiers("import http.server"))

    def test_from_imports_including_submodule_form(self) -> None:
        self.assertIn(("PROHIBITED", "socketserver"), tiers("from socketserver import TCPServer"))
        self.assertIn(("PROHIBITED", "http.server"), tiers("from http import server"))
        self.assertIn(("PROHIBITED", "urllib.request"), tiers("from urllib import request as r"))
        self.assertIn(("PROHIBITED", "http.client"), tiers("from http.client import HTTPConnection"))

    def test_dynamic_imports(self) -> None:
        self.assertIn(("PROHIBITED", "asyncio"), tiers("__import__('asyncio')"))
        self.assertIn(("PROHIBITED", "websockets"), tiers("import importlib\nimportlib.import_module('websockets')"))
        self.assertIn(("UNVERIFIABLE", "import_module(<expr>)"), tiers("import importlib\nimportlib.import_module(name)"))
        self.assertIn(("ALLOWED", "import_module(<expr>)"),
                      tiers("import importlib\nimportlib.import_module(n)  # constraint-scan: allow-dynamic-import"))

    def test_exec_with_import_is_review(self) -> None:
        self.assertIn(("REVIEW", "exec(...)"), tiers("exec('import asyncio')"))

    def test_review_tier(self) -> None:
        self.assertIn(("REVIEW", "selectors"), tiers("import selectors"))

    def test_names_in_strings_and_comments_are_not_imports(self) -> None:
        src = '"""uses asyncio? no."""\n# import flask\nNAMES = ["asyncio", "http.server"]\nprint("import requests")\n'
        self.assertEqual(tiers(src), [])

    def test_allowed_modules(self) -> None:
        self.assertEqual(tiers("import socket, threading, struct, json, hashlib\nfrom http import HTTPStatus"), [])
        self.assertEqual(tiers("from . import sibling\nfrom .x import y"), [])


class ProjectScanTests(unittest.TestCase):
    def test_project_has_no_blocking_findings(self) -> None:
        files, findings = cs.scan_project(ROOT)
        self.assertGreater(len(files), 40)
        blocking = [str(f) for f in findings if f.tier in {"PROHIBITED", "UNVERIFIABLE"}]
        self.assertEqual(blocking, [])

    def test_transport_algorithms_not_duplicated_in_server_or_client(self) -> None:
        import ast

        suspicious = ("Cubic", "Congestion", "Pacer", "PacedSender", "Reliability", "FlowWindow", "Scheduler")
        hits = []
        for sub in ("src/server", "src/client"):
            for path in (ROOT / sub).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and any(s in node.name for s in suspicious):
                        hits.append(f"{path.relative_to(ROOT)}:{node.name}")
        self.assertEqual(hits, [])

    def test_exactly_two_entry_points(self) -> None:
        mains = []
        for path in [ROOT / "server.py", ROOT / "client.py", *(ROOT / "src").rglob("*.py")]:
            if '__name__ == "__main__"' in path.read_text(encoding="utf-8"):
                mains.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(sorted(mains), ["client.py", "server.py"])


if __name__ == "__main__":
    unittest.main()
