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



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed local Vault dev secrets for Maintainer's Copilot.")
    parser.add_argument("--write-demo-anthropic-placeholder", action="store_true")
    return parser.parse_args()


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
    wrote_paths: list[str] = []
    skipped: list[str] = []

    try:
        client.write_kv_v2_secret(
            paths["jwt"],
            {"jwt_secret": env_or_local("API_JWT_SECRET", local_env, "dev-only-jwt-secret-change-me")},
        )
        wrote_paths.append(paths["jwt"])
        client.write_kv_v2_secret(
            paths["postgres"],
            {"password": env_or_local("POSTGRES_PASSWORD", local_env, "postgres")},
        )
        wrote_paths.append(paths["postgres"])
        minio_payload = {
            "access_key": env_or_local("API_MINIO_ACCESS_KEY", local_env, "minioadmin"),
            "secret_key": env_or_local("API_MINIO_SECRET_KEY", local_env, "minioadmin"),
        }
        client.write_kv_v2_secret(paths["minio_access"], minio_payload)
        wrote_paths.append(paths["minio_access"])

        anthropic_key = env_or_local("ANTHROPIC_API_KEY", local_env)
        if anthropic_key:
            client.write_kv_v2_secret(paths["anthropic"], {"api_key": anthropic_key})
            wrote_paths.append(paths["anthropic"])
        elif args.write_demo_anthropic_placeholder:
            client.write_kv_v2_secret(paths["anthropic"], {"api_key": "placeholder-not-required"})
            wrote_paths.append(paths["anthropic"])
        else:
            skipped.append(paths["anthropic"])
    except VaultSecretError as exc:
        print(f"Vault seeding failed: {exc}")
        return 1

    for path in wrote_paths:
        print(f"WROTE {path}")
    for path in skipped:
        print(f"SKIPPED {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
