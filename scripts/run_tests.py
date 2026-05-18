#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_suite(label: str, workdir: Path) -> int:
    python_path = venv_python()
    if not python_path.exists():
        print("Missing repo-local .venv. Run scripts/bootstrap_dev.py first.", file=sys.stderr)
        return 1

    print(f"==> {label}")
    result = subprocess.run([str(python_path), "-m", "pytest", "tests"], cwd=workdir)
    print()
    return result.returncode


def main() -> int:
    api_status = run_suite("API tests", ROOT / "services" / "api")
    model_status = run_suite("Model-server tests", ROOT / "services" / "model-server")
    return 0 if api_status == 0 and model_status == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

