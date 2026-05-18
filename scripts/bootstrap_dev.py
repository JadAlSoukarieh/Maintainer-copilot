#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv() -> Path:
    python_path = venv_python()
    if python_path.exists():
        return python_path
    print(f"Creating virtual environment at {VENV_DIR}")
    venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    return python_path


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    rendered = " ".join(cmd)
    print(f"> {rendered}")
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def main() -> int:
    python_path = ensure_venv()

    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(python_path), "-m", "pip", "install", "-e", "./services/api[dev]"], cwd=ROOT)
    run([str(python_path), "-m", "pip", "install", "-e", "./services/model-server[dev]"], cwd=ROOT)

    print()
    print("Bootstrap complete.")
    print("Test commands:")
    print("  ./.venv/bin/python scripts/run_tests.py")
    print("  cd services/api && ../../.venv/bin/python -m pytest tests")
    print("  cd services/model-server && ../../.venv/bin/python -m pytest tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

