from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_vault_dev_secrets = _load_module("seed_vault_dev_secrets", "scripts/seed_vault_dev_secrets.py")
check_vault_secrets = _load_module("check_vault_secrets", "scripts/check_vault_secrets.py")


def test_vault_secret_paths_use_existing_prefix() -> None:
    paths = seed_vault_dev_secrets.build_secret_paths(seed_vault_dev_secrets.Settings())

    assert paths["jwt"] == "secret/data/maintainers-copilot/api"
    assert paths["postgres"] == "secret/data/maintainers-copilot/postgres"
    assert paths["anthropic"] == "secret/data/maintainers-copilot/anthropic"


def test_env_file_loader_parses_simple_assignments(tmp_path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("VAULT_TOKEN=test-token\nAPI_JWT_SECRET=secret-value\n", encoding="utf-8")

    values = seed_vault_dev_secrets.load_env_file(env_file)

    assert values["VAULT_TOKEN"] == "test-token"
    assert values["API_JWT_SECRET"] == "secret-value"


def test_check_script_accepts_demo_placeholder_only_with_flag() -> None:
    payload = {"api_key": "placeholder-not-required"}

    assert check_vault_secrets._payload_has_required_fields(payload, ["api_key"], allow_demo_placeholders=True) is True
    assert check_vault_secrets._payload_has_required_fields(payload, ["api_key"], allow_demo_placeholders=False) is False
