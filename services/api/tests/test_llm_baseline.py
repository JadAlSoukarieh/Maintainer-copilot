from __future__ import annotations

import importlib.util
import io
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from maintcopilot_api.infra.anthropic_client import (
    AnthropicClassificationResponse,
    AnthropicKeyResolutionError,
    resolve_anthropic_api_key,
    resolve_anthropic_api_key_details,
)
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import JsonFormatter, log_with_context
from maintcopilot_api.services.llm_baseline.metrics import compute_metrics, estimate_cost_usd
from maintcopilot_api.services.llm_baseline.parsing import InvalidLLMBaselineOutputError, normalize_label, parse_label_response
from maintcopilot_api.services.llm_baseline.runner import load_existing_predictions, run_baseline


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "scripts" / "run_llm_baseline.py"


class FakeVaultClient:
    def __init__(self, payload: dict[str, Any] | None = None, *, should_raise: bool = False) -> None:
        self._payload = payload
        self._should_raise = should_raise

    def read_kv_v2_secret(self, path: str) -> dict[str, Any] | None:
        if self._should_raise:
            raise RuntimeError("boom")
        return self._payload


class FakeClassifierClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def classify(self, prompt: str, *, max_tokens: int = 50, temperature: float = 0.0) -> AnthropicClassificationResponse:
        del prompt, max_tokens, temperature
        return AnthropicClassificationResponse(
            raw_output='{"label":"question"}',
            input_tokens=123,
            output_tokens=7,
            model_name="claude-haiku-4-5-20251001",
        )


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_llm_baseline_script", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load run_llm_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_test_fixture(path: Path) -> None:
    rows = [
        {
            "issue_id": "1",
            "issue_number": 1001,
            "url": "https://example.com/1",
            "title": "How do I use this API?",
            "body": "I need help using the command line flags.",
            "label": "question",
        },
        {
            "issue_id": "2",
            "issue_number": 1002,
            "url": "https://example.com/2",
            "title": "Feature request: add recursive chmod",
            "body": "Please add a recursive flag.",
            "label": "feature",
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    (path.parent / "data_hash.txt").write_text("test-hash\n", encoding="utf-8")


def test_label_normalization() -> None:
    assert normalize_label("bug") == "bug"
    assert normalize_label("Feature Request") == "feature"
    assert normalize_label("documentation") == "docs"
    assert normalize_label("support") == "question"
    assert normalize_label("nonsense") is None


def test_strict_json_parsing() -> None:
    assert parse_label_response('{"label":"bug"}') == "bug"


def test_fenced_json_parsing() -> None:
    assert parse_label_response('```json\n{"label":"docs"}\n```') == "docs"


def test_invalid_output_handling() -> None:
    with pytest.raises(InvalidLLMBaselineOutputError):
        parse_label_response('{"label":"unknown"}')
    with pytest.raises(InvalidLLMBaselineOutputError):
        parse_label_response("not-json")


def test_metrics_computation() -> None:
    metrics = compute_metrics(
        ["bug", "feature", "docs", "question"],
        ["bug", "feature", "question", "question"],
    )
    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["per_class_f1"]["bug"] == pytest.approx(1.0)
    assert metrics["per_class_f1"]["docs"] == pytest.approx(0.0)
    assert metrics["confusion_matrix"]["labels"] == ["bug", "feature", "docs", "question"]


def test_cost_computation() -> None:
    assert estimate_cost_usd(
        input_tokens=1000,
        output_tokens=100,
        input_price_per_mtok=1.0,
        output_price_per_mtok=5.0,
    ) == pytest.approx(0.0015)


def test_resume_skip_behavior(tmp_path: Path) -> None:
    test_path = tmp_path / "test.jsonl"
    write_test_fixture(test_path)
    output_dir = tmp_path / "output"

    summary = run_baseline(
        test_path=test_path,
        output_dir=output_dir,
        model_name="claude-haiku-4-5-20251001",
        limit=None,
        resume=True,
        overwrite=False,
        dry_run=True,
        max_body_chars=6000,
        input_price_per_mtok=1.0,
        output_price_per_mtok=5.0,
        classifier_client=None,
    )
    assert summary["new_predictions"] == 2

    second_summary = run_baseline(
        test_path=test_path,
        output_dir=output_dir,
        model_name="claude-haiku-4-5-20251001",
        limit=None,
        resume=True,
        overwrite=False,
        dry_run=True,
        max_body_chars=6000,
        input_price_per_mtok=1.0,
        output_price_per_mtok=5.0,
        classifier_client=None,
    )
    assert second_summary["new_predictions"] == 0
    assert len(load_existing_predictions(output_dir / "predictions.jsonl")) == 2


def test_dry_run_output_creation(tmp_path: Path) -> None:
    test_path = tmp_path / "test.jsonl"
    write_test_fixture(test_path)
    output_dir = tmp_path / "output"

    summary = run_baseline(
        test_path=test_path,
        output_dir=output_dir,
        model_name="claude-haiku-4-5-20251001",
        limit=1,
        resume=False,
        overwrite=False,
        dry_run=True,
        max_body_chars=6000,
        input_price_per_mtok=1.0,
        output_price_per_mtok=5.0,
        classifier_client=None,
    )

    assert summary["dry_run"] is True
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    cost_report = json.loads((output_dir / "cost_report.json").read_text(encoding="utf-8"))
    predictions = load_existing_predictions(output_dir / "predictions.jsonl")
    assert metrics["dry_run"] is True
    assert cost_report["dry_run"] is True
    assert predictions[0]["dry_run"] is True
    assert predictions[0]["model_name"].startswith("dry-run::")


def test_missing_key_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(require_vault=False, anthropic_api_key_secret_path=None)
    with pytest.raises(AnthropicKeyResolutionError):
        resolve_anthropic_api_key(settings, vault_client=None)


def test_env_fallback_allowed_when_vault_not_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-secret")
    settings = Settings(require_vault=False, anthropic_api_key_secret_path=None)
    assert resolve_anthropic_api_key(settings, vault_client=None) == "sk-ant-fake-secret"


def test_env_key_is_preferred_over_vault_placeholder_when_vault_not_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-secret")
    settings = Settings(require_vault=False, anthropic_api_key_secret_path="secret/data/app/anthropic")

    resolution = resolve_anthropic_api_key_details(
        settings,
        vault_client=FakeVaultClient(payload={"api_key": "placeholder-not-required"}),
        allow_env_fallback=True,
    )

    assert resolution.key_source == "env"
    assert resolution.key_present is True
    assert resolution.key_length == len("sk-ant-env-secret")
    assert resolution.prefix_ok is True
    assert resolution.api_key == "sk-ant-env-secret"


def test_env_fallback_rejected_for_deployed_path_when_vault_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-secret")
    settings = Settings(require_vault=True, anthropic_api_key_secret_path="secret/data/app/anthropic")
    with pytest.raises(AnthropicKeyResolutionError):
        resolve_anthropic_api_key(settings, vault_client=FakeVaultClient(payload=None), for_cli=False)


def test_vault_placeholder_is_skipped_when_env_fallback_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-secret")
    settings = Settings(require_vault=True, anthropic_api_key_secret_path="secret/data/app/anthropic")

    resolution = resolve_anthropic_api_key_details(
        settings,
        vault_client=FakeVaultClient(payload={"api_key": "placeholder-not-required"}),
        allow_env_fallback=True,
    )

    assert resolution.key_source == "env"
    assert resolution.api_key == "sk-ant-env-secret"


def test_vault_key_is_used_when_required_and_not_placeholder() -> None:
    settings = Settings(require_vault=True, anthropic_api_key_secret_path="secret/data/app/anthropic")

    resolution = resolve_anthropic_api_key_details(
        settings,
        vault_client=FakeVaultClient(payload={"api_key": "sk-ant-vault-secret"}),
        allow_env_fallback=True,
    )

    assert resolution.key_source == "vault"
    assert resolution.api_key == "sk-ant-vault-secret"


def test_cli_env_fallback_allowed_only_with_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    test_path = tmp_path / "test.jsonl"
    write_test_fixture(test_path)
    output_dir = tmp_path / "output"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-cli-secret")

    module = load_script_module()
    exit_code = module.main(
        [
            "--test-path",
            str(test_path),
            "--output-dir",
            str(output_dir),
            "--limit",
            "1",
            "--no-resume",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "sk-ant-cli-secret" not in captured.out
    assert "sk-ant-cli-secret" not in captured.err

    monkeypatch.setattr(module, "AnthropicClassifierClient", FakeClassifierClient)
    exit_code = module.main(
        [
            "--test-path",
            str(test_path),
            "--output-dir",
            str(output_dir),
            "--limit",
            "1",
            "--no-resume",
            "--overwrite",
            "--allow-env-key",
        ]
    )
    assert exit_code == 0
    predictions = load_existing_predictions(output_dir / "predictions.jsonl")
    assert predictions[0]["predicted_label"] == "question"


def test_fake_key_never_appears_in_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-log-secret")
    logger = logging.getLogger("llm-baseline-test")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_with_context(logger, "info", "testing.secret.redaction", anthropic_api_key="sk-ant-log-secret")

    rendered = stream.getvalue()
    assert "sk-ant-log-secret" not in rendered
    assert "[REDACTED]" in rendered
