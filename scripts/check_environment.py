"""Environment and structure check. Run from anywhere: ``python scripts/check_environment.py``.

Checks: Python version, required project files, absence of third-party dependency manifests,
and the AST constraint scan. Exits non-zero on any failure. Opens no sockets.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import constraint_scan  # noqa: E402  (local script module)

MIN_PYTHON = (3, 10)
REQUIRED_FILES = [
    "server.py",
    "client.py",
    "src/server/frontend/static/index.html",
    "src/server/frontend/static/css/style.css",
    "src/server/frontend/static/js/app.js",
    "src/client/frontend/static/index.html",
    "src/client/frontend/static/css/style.css",
    "src/client/frontend/static/js/app.js",
]
DEPENDENCY_MANIFESTS = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "package.json"]


def main() -> int:
    ok = True
    print(f"python   : {platform.python_version()} ({sys.executable})")
    print(f"platform : {platform.platform()}")
    if sys.version_info < MIN_PYTHON:
        print(f"FAIL python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required")
        ok = False
    else:
        print(f"PASS python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")

    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    if missing:
        ok = False
        print("FAIL missing files: " + ", ".join(missing))
    else:
        print(f"PASS required files present ({len(REQUIRED_FILES)})")

    manifests = [f for f in DEPENDENCY_MANIFESTS if (ROOT / f).exists()]
    if manifests:
        print("WARN dependency manifests found (review for third-party packages): " + ", ".join(manifests))
    else:
        print("PASS no dependency manifests: standard library only")

    files, findings = constraint_scan.scan_project(ROOT)
    blocking = constraint_scan.has_blocking_findings(findings)
    print(f"{'FAIL' if blocking else 'PASS'} constraint scan over {len(files)} files "
          f"({len(findings)} findings; see scripts/constraint_scan.py for details)")
    ok = ok and not blocking

    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
