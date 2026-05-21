from __future__ import annotations

from pathlib import Path

import pytest

from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.startup import (
    StartupValidationError,
    resolve_required_secrets,
    validate_eval_thresholds,
    validate_model_server_health,
    validate_tracing_policy,
)


ROOT = Path(__file__).resolve().parents[3]


class FakeVaultClient:
    def __init__(self, secrets: dict[str, dict[str, str]] | None = None, *, healthy: bool = True) -> None:
        self.secrets = secrets or {}
        self.healthy = healthy

    def check_health(self) -> bool:
        return self.healthy

    def read_kv_v2_secret(self, path: str):
        return self.secrets.get(path)


def test_require_vault_missing_jwt_secret_fails() -> None:
    settings = Settings(require_vault=True, jwt_secret_path="secret/data/app/jwt")

    with pytest.raises(StartupValidationError):
        resolve_required_secrets(settings, FakeVaultClient(secrets={}))


def test_local_fallback_allowed_when_vault_disabled() -> None:
    settings = Settings(require_vault=False)

    assert settings.require_vault is False


def test_zero_eval_threshold_fails_validation(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text(
        """
classification:
  min_accuracy: 0.0
  min_macro_f1: 0.55
rag_retrieval:
  min_hit_at_5: 0.4
  min_mrr_at_10: 0.2
rag_generation:
  min_answer_relevancy: 0.25
  min_faithfulness: 0.4
  min_citation_coverage: 0.6
  min_groundedness_pass_rate: 0.3
""",
        encoding="utf-8",
    )

    with pytest.raises(StartupValidationError):
        validate_eval_thresholds(thresholds)


def test_missing_tracing_backend_fails_only_when_required() -> None:
    validate_tracing_policy(Settings(require_vault=False, require_tracing=False))

    with pytest.raises(StartupValidationError):
        validate_tracing_policy(Settings(require_vault=False, require_tracing=True, tracing_backend_url=None))


def test_missing_model_server_health_fails_only_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    import maintcopilot_api.infra.startup as startup_module

    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(startup_module.httpx, "get", lambda *args, **kwargs: FakeResponse())

    validate_model_server_health(Settings(require_vault=False, require_model_server_health=False))

    with pytest.raises(StartupValidationError):
        validate_model_server_health(Settings(require_vault=False, require_model_server_health=True))
