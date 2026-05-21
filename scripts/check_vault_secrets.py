#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services/api"))

from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.vault import VaultClient, VaultSecretError


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_or_local(name: str, local_env: dict[str, str], default: str | None = None) -> str | None:
    return os.getenv(name) or local_env.get(name) or default


def build_secret_paths(settings: Settings) -> dict[str, str]:
    return {
        "jwt": settings.jwt_secret_path or "secret/data/maintainers-copilot/api",
        "postgres": settings.db_password_secret_path or "secret/data/maintainers-copilot/postgres",
        "minio_access": settings.minio_access_key_secret_path or "secret/data/maintainers-copilot/minio",
        "minio_secret": settings.minio_secret_key_secret_path or "secret/data/maintainers-copilot/minio",
        "anthropic": settings.anthropic_api_key_secret_path or "secret/data/maintainers-copilot/anthropic",
    }


def _payload_has_required_fields(
    payload: dict[str, str] | None,
    field_names: list[str],
    *,
    allow_demo_placeholders: bool,
) -> bool:
    if not payload:
        return False
    for field_name in field_names:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return False
        if field_name == "api_key" and not allow_demo_placeholders and value == "placeholder-not-required":
            return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local Vault dev secrets for Maintainer's Copilot.")
    parser.add_argument("--require-anthropic", action="store_true")
    parser.add_argument("--allow-demo-placeholders", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_env = load_env_file(REPO_ROOT / ".env.local")
    settings = Settings()
    paths = build_secret_paths(settings)

    vault_addr = env_or_local("VAULT_ADDR", local_env, "http://localhost:8200")
    vault_token = env_or_local("VAULT_TOKEN", local_env)
    if not vault_token:
        print("Missing VAULT_TOKEN. Set it in the environment or .env.local.")
        return 2

    client = VaultClient(addr=vault_addr, token=vault_token)
    required = {
        paths["jwt"]: ["jwt_secret"],
        paths["postgres"]: ["password"],
        paths["minio_access"]: ["access_key", "secret_key"],
    }
    if args.require_anthropic:
        required[paths["anthropic"]] = ["api_key"]

    missing: list[str] = []
    for path, field_names in required.items():
        try:
            payload = client.read_kv_v2_secret(path)
        except VaultSecretError:
            missing.append(path)
            continue
        if not _payload_has_required_fields(payload, field_names, allow_demo_placeholders=args.allow_demo_placeholders):
            missing.append(path)
            continue
        print(f"OK {path}")

    if missing:
        for path in missing:
            print(f"MISSING {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
