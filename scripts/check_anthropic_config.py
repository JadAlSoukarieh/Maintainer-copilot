#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
SOURCE_CANDIDATES = [
    SCRIPT_PATH.parents[1] / "services/api",
    SCRIPT_PATH.parents[1],
]
for candidate in SOURCE_CANDIDATES:
    if (candidate / "maintcopilot_api").exists():
        sys.path.insert(0, str(candidate))
        break

from maintcopilot_api.infra.anthropic_client import (  # noqa: E402
    read_vault_anthropic_key_metadata,
    resolve_anthropic_api_key_details,
)
from maintcopilot_api.infra.config import Settings  # noqa: E402
from maintcopilot_api.infra.vault import VaultClient  # noqa: E402


PLACEHOLDER_MARKERS = ("placeholder", "replace", "your_key", "...")


def main() -> int:
    settings = Settings()
    vault_client = VaultClient(addr=settings.vault_addr, token=settings.vault_token)

    env_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    env_key_present = bool(env_key)
    env_key_length = len(env_key)
    env_prefix_ok = env_key.startswith("sk-ant-")

    resolution = resolve_anthropic_api_key_details(
        settings,
        vault_client,
        allow_env_fallback=settings.chat_allow_env_key_fallback,
        for_cli=False,
    )
    vault_meta = read_vault_anthropic_key_metadata(settings, vault_client)

    selected_source = resolution.key_source if resolution.key_source in {"env", "vault"} else "missing"
    placeholder_detected = resolution.key_source == "placeholder" or (
        selected_source == "env" and _looks_placeholder(env_key)
    )

    payload = {
        "env_key_present": env_key_present,
        "env_key_length": env_key_length,
        "env_prefix_ok": env_prefix_ok,
        "vault_required": settings.require_vault,
        "env_fallback_allowed": settings.chat_allow_env_key_fallback,
        "selected_source": selected_source,
        "selected_key_present": resolution.key_present,
        "selected_key_length": resolution.key_length,
        "selected_prefix_ok": resolution.prefix_ok,
        "placeholder_detected": placeholder_detected,
    }
    print(json.dumps(payload, indent=2))
    return 0


def _looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    return bool(value) and any(marker in lowered for marker in PLACEHOLDER_MARKERS)


if __name__ == "__main__":
    raise SystemExit(main())
