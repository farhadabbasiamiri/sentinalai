"""Verify that a machine is ready to run SentinelAI as described in README.md.

Usage (from the repository root):
    python scripts/check_setup.py               # backend + frontend checks
    python scripts/check_setup.py --backend-only

Exit code 0 means every required check passed; warnings do not fail the run.
Only local, read-only checks are performed: no network calls, no data changes.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import socket
# subprocess is only used to read `node --version` / `npm --version` (fixed arguments, no shell).
import subprocess  # nosec B404
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 10)
MIN_NODE = (20, 19)  # Vite 8 requires Node ^20.19 or >=22.12

REQUIRED_FILES = [
    "requirements.txt",
    "backend/app/main.py",
    "backend/app/core/policy.py",
    "backend/app/policies/governance.md",
    "data/evaluation_cases.json",
    "data/synthetic_agents.json",
    "data/synthetic_agents.csv",
    "frontend/package.json",
    "frontend/package-lock.json",
]
BACKEND_PACKAGES = ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "httpx", "pytest"]

results: list[tuple[str, str, str]] = []  # (status, check, detail)


def record(status: str, check: str, detail: str = "") -> None:
    results.append((status, check, detail))


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def tool_version(command: list[str]) -> str | None:
    executable = shutil.which(command[0])
    if not executable:
        return None
    try:
        completed = subprocess.run([executable, *command[1:]], capture_output=True, text=True, timeout=20, check=False)  # nosec B603
    except (OSError, subprocess.SubprocessError):
        return None
    return (completed.stdout or completed.stderr).strip() or None


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def check_python() -> None:
    current = sys.version_info[:2]
    label = f"Python {sys.version.split()[0]}"
    if current >= MIN_PYTHON:
        record("OK", "Python version", label)
    else:
        record("FAIL", "Python version", f"{label}; need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
    if sys.prefix == sys.base_prefix and not os.getenv("CI"):
        record("WARN", "Virtual environment", "Not active. README recommends: python -m venv .venv")
    else:
        record("OK", "Virtual environment", "active" if sys.prefix != sys.base_prefix else "CI runner")


def check_backend_packages() -> None:
    missing = [name for name in BACKEND_PACKAGES if importlib.util.find_spec(name) is None]
    if missing:
        record("FAIL", "Backend packages", f"missing {', '.join(missing)}; run: python -m pip install -r requirements.txt")
    else:
        record("OK", "Backend packages", ", ".join(BACKEND_PACKAGES))
    if importlib.util.find_spec("gradio") is None:
        record("INFO", "Optional Gradio dashboard", "not installed (pip install -r requirements-gradio.txt)")
    else:
        record("OK", "Optional Gradio dashboard", "installed")


def check_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        record("FAIL", "Repository files", "missing " + ", ".join(missing))
    else:
        record("OK", "Repository files", f"{len(REQUIRED_FILES)} required files present")


def check_frontend() -> None:
    node = tool_version(["node", "--version"])
    if node is None:
        record("FAIL", "Node.js", "not found; install Node.js 20.19+ or 22+")
    elif version_tuple(node)[:2] < MIN_NODE:
        record("FAIL", "Node.js", f"{node}; Vite 8 needs 20.19+ or 22.12+")
    else:
        record("OK", "Node.js", node)
    npm = tool_version(["npm", "--version"])
    record("OK" if npm else "FAIL", "npm", npm or "not found")
    if (ROOT / "frontend" / "node_modules").exists():
        record("OK", "Frontend dependencies", "frontend/node_modules present")
    else:
        record("WARN", "Frontend dependencies", "not installed yet; run: cd frontend && npm ci")


def check_runtime() -> None:
    for port, service in ((8000, "Backend API port 8000"), (5173, "Frontend port 5173")):
        if port_free(port):
            record("OK", service, "free")
        else:
            record("WARN", service, "already in use (another server may be running)")
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if not ollama_url:
        record("INFO", "Ollama", "OLLAMA_URL not set; reviews use the deterministic fallback")
    elif urlparse(ollama_url).hostname in {"localhost", "127.0.0.1", "::1"}:
        record("OK", "Ollama", f"local endpoint {ollama_url}")
    else:
        record("WARN", "Ollama", f"{ollama_url} is not local; the backend will ignore it by design")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend-only", action="store_true", help="skip Node.js / frontend checks")
    args = parser.parse_args()

    check_python()
    check_backend_packages()
    check_files()
    if not args.backend_only:
        check_frontend()
    check_runtime()

    width = max(len(check) for _, check, _ in results)
    print("SentinelAI setup check\n")
    for status, check, detail in results:
        print(f"[{status:<4}] {check:<{width}}  {detail}")
    failures = sum(status == "FAIL" for status, _, _ in results)
    warnings = sum(status == "WARN" for status, _, _ in results)
    print(f"\n{len(results)} checks: {failures} failed, {warnings} warnings")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
