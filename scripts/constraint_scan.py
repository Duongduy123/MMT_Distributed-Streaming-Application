"""AST-based constraint scanner: finds prohibited / review-worthy imports in Python sources.

Scope (default): server.py, client.py, src/, tests/, scripts/  -- relative to the project root.
Markdown and other non-Python files are never scanned. ``congestion_control/`` (the original,
untouched copy of the CUBIC/Pacer work) is audited separately.

Detected forms
    import x / import x as y                          -> checked against the tiers below
    from x import y / from x import y as z            -> checks ``x`` and ``x.y``
                                                         (so ``from http import server`` is http.server)
    __import__("x"), importlib.import_module("x"),
    importlib.__import__("x"), import_module("x")     -> literal first arg checked
    the same calls with a NON-literal first argument  -> UNVERIFIABLE
    exec(...) / eval(...) of a string containing "import" -> REVIEW

Only ``Import``/``ImportFrom`` nodes and those call forms are inspected, so prohibited names in
strings, comments or docstrings (including this file's own tables) are NOT reported.

A line ending in ``# constraint-scan: allow-dynamic-import`` downgrades an UNVERIFIABLE
dynamic import to ALLOWED (used by the import-safety test that walks every package module).

Exit status: 1 if any PROHIBITED or UNVERIFIABLE finding exists, otherwise 0.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = ("server.py", "client.py", "src", "tests", "scripts")
PRAGMA = "constraint-scan: allow-dynamic-import"

# Assignment PDF section 8 + team constraints (docs/CONSTRAINT_AUDIT.md).
PROHIBITED: dict[str, str] = {
    "flask": "HTTP framework (PDF section 8)",
    "django": "HTTP framework (PDF section 8)",
    "fastapi": "HTTP framework",
    "starlette": "HTTP framework",
    "tornado": "HTTP/networking framework",
    "aiohttp": "HTTP/networking framework",
    "websockets": "WebSockets (PDF section 8)",
    "websocket": "WebSockets (PDF section 8)",
    "socketio": "Socket.IO / WebSockets",
    "engineio": "Socket.IO / WebSockets",
    "scapy": "packet-crafting framework",
    "aioquic": "prebuilt QUIC transport",
    "twisted": "networking framework",
    "gevent": "networking/concurrency framework",
    "eventlet": "networking/concurrency framework",
    "requests": "high-level HTTP client",
    "httpx": "high-level HTTP client",
    "urllib3": "high-level HTTP client",
    "urllib.request": "high-level HTTP client (stdlib)",
    "http.server": "HTTP server framework (stdlib)",
    "http.client": "high-level HTTP client (stdlib)",
    "socketserver": "server framework (stdlib)",
    "asyncio": "async networking abstractions (team rule, D11)",
    "multiprocessing": "extra OS processes (two-process architecture)",
    "subprocess": "extra OS processes (two-process architecture)",
    "cryptography": "third-party dependency pending decision D9",
    "Crypto": "third-party dependency pending decision D9 (PyCryptodome)",
}

REVIEW: dict[str, str] = {
    "selectors": "I/O multiplexing; allowed only if the team approves (D11 chose threading)",
    "select": "I/O multiplexing; allowed only if the team approves (D11 chose threading)",
    "ssl": "TLS over TCP; relevant only to D9",
    "importlib": "dynamic imports must be reviewed",
}

_DYNAMIC_IMPORT_FUNCS = {"__import__", "import_module"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    tier: str  # PROHIBITED | UNVERIFIABLE | REVIEW | ALLOWED
    module: str
    reason: str

    def __str__(self) -> str:
        return f"{self.tier:<12} {self.path}:{self.line}  {self.module}  -- {self.reason}"


def _classify(module: str) -> tuple[str, str] | None:
    """Return (tier, reason) for ``module`` or ``None`` if it is not listed."""
    for table, tier in ((PROHIBITED, "PROHIBITED"), (REVIEW, "REVIEW")):
        for name, reason in table.items():
            if module == name or module.startswith(name + "."):
                return tier, reason
    return None


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, lines: list[str]) -> None:
        self.rel_path = rel_path
        self.lines = lines
        self.findings: list[Finding] = []

    def _add(self, node: ast.AST, module: str) -> None:
        hit = _classify(module)
        if hit:
            self.findings.append(Finding(self.rel_path, node.lineno, hit[0], module, hit[1]))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(node, alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module:
            before = len(self.findings)
            self._add(node, node.module)
            if len(self.findings) == before:  # parent not listed: check submodule forms
                for alias in node.names:
                    self._add(node, f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        if name in _DYNAMIC_IMPORT_FUNCS:
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self._add(node, arg.value)
            else:
                line = self.lines[node.lineno - 1] if node.lineno <= len(self.lines) else ""
                tier = "ALLOWED" if PRAGMA in line else "UNVERIFIABLE"
                self.findings.append(
                    Finding(self.rel_path, node.lineno, tier, f"{name}(<expr>)",
                            "dynamic import with non-literal module name")
                )
        elif name in {"exec", "eval"} and isinstance(node.func, ast.Name):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "import" in arg.value:
                    self.findings.append(
                        Finding(self.rel_path, node.lineno, "REVIEW", f"{name}(...)",
                                "executes source text containing 'import'")
                    )
        self.generic_visit(node)


def scan_source(source: str, rel_path: str = "<string>") -> list[Finding]:
    """Scan one Python source string."""
    tree = ast.parse(source, filename=rel_path)
    visitor = _Visitor(rel_path, source.splitlines())
    visitor.visit(tree)
    return visitor.findings


def iter_python_files(root: Path, targets: tuple[str, ...] = DEFAULT_TARGETS) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = root / target
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in sorted(path.rglob("*.py")) if "__pycache__" not in p.parts)
    return files


def scan_project(root: Path = PROJECT_ROOT, targets: tuple[str, ...] = DEFAULT_TARGETS) -> tuple[list[Path], list[Finding]]:
    """Scan every Python file under ``targets``. Returns (files_scanned, findings)."""
    files = iter_python_files(root, targets)
    findings: list[Finding] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        findings.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return files, findings


def has_blocking_findings(findings: list[Finding]) -> bool:
    return any(f.tier in {"PROHIBITED", "UNVERIFIABLE"} for f in findings)


def main() -> int:
    files, findings = scan_project()
    print(f"constraint scan: {len(files)} Python files under {', '.join(DEFAULT_TARGETS)}")
    for finding in findings:
        print("  " + str(finding))
    counts = {t: sum(f.tier == t for f in findings) for t in ("PROHIBITED", "UNVERIFIABLE", "REVIEW", "ALLOWED")}
    print("summary: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    blocking = has_blocking_findings(findings)
    print("RESULT: " + ("FAIL" if blocking else "PASS"))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
