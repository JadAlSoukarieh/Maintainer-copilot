from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

from maintcopilot_api.infra.anthropic_client import resolve_anthropic_api_key
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.minio import MinioClient, MinioStorageError
from maintcopilot_api.infra.vault import VaultClient, VaultSecretError


class StartupValidationError(RuntimeError):
    pass


def validate_startup(settings: Settings, vault_client: VaultClient, *, repo_root: Path) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {"warnings": []}

    if settings.require_vault:
        if not vault_client.check_health():
            raise StartupValidationError("Vault is required but unreachable.")
        diagnostics["secrets"] = resolve_required_secrets(settings, vault_client)
    else:
        logging.getLogger("app.startup").warning("Vault is disabled; using local/demo env fallback where configured.")
        diagnostics["secrets"] = {"mode": "env_fallback_allowed"}

    if settings.validate_eval_thresholds:
        validate_eval_thresholds(repo_root / "evals/eval_thresholds.yaml")

    validate_required_reports(repo_root=repo_root, env=settings.env, warnings=diagnostics["warnings"])
    validate_tracing_policy(settings)
    validate_model_server_health(settings)
    return diagnostics


def init_minio(minio_client: MinioClient, *, repo_root: Path, warnings: list[str]) -> None:
    """Ensure the MinIO bucket exists and upload any committed report files."""
    try:
        minio_client.ensure_bucket()
    except MinioStorageError as exc:
        warnings.append(f"MinIO bucket init failed (non-fatal): {exc}")
        return

    _upload_reports_to_minio(minio_client, repo_root=repo_root, warnings=warnings)
    _upload_artifact_manifest(minio_client, repo_root=repo_root, warnings=warnings)


def _upload_reports_to_minio(minio_client: MinioClient, *, repo_root: Path, warnings: list[str]) -> None:
    report_files = [
        "reports/eval_report.json",
        "reports/rag_generation_eval_report.json",
        "reports/rag_generation_human_review.md",
    ]
    for rel_path in report_files:
        path = repo_root / rel_path
        if not path.exists():
            continue
        try:
            if path.suffix == ".json":
                import json
                minio_client.put_json(rel_path, json.loads(path.read_text(encoding="utf-8")))
            else:
                minio_client.put_bytes(rel_path, path.read_bytes(), content_type="text/markdown")
            logging.getLogger("app.startup").info("minio.report_uploaded", extra={"event_fields": {"key": rel_path}})
        except MinioStorageError as exc:
            warnings.append(f"MinIO report upload failed for {rel_path!r}: {exc}")


def _upload_artifact_manifest(minio_client: MinioClient, *, repo_root: Path, warnings: list[str]) -> None:
    manifest_path = repo_root / "artifacts/classifier/transformer/model_card.md"
    if not manifest_path.exists():
        return
    try:
        minio_client.put_bytes(
            "artifacts/classifier/transformer/model_card.md",
            manifest_path.read_bytes(),
            content_type="text/markdown",
        )
    except MinioStorageError as exc:
        warnings.append(f"MinIO artifact manifest upload failed: {exc}")


def resolve_required_secrets(settings: Settings, vault_client: VaultClient) -> dict[str, Any]:
    resolved: dict[str, Any] = {"warnings": []}
    jwt_secret = _resolve_vault_field(
        vault_client,
        settings.jwt_secret_path,
        field_name="jwt_secret",
        error_message="JWT signing key could not be resolved from Vault.",
        required=True,
    )
    settings.jwt_secret = str(jwt_secret)
    resolved["jwt_secret"] = "resolved"

    if settings.require_llm_key:
        resolve_anthropic_api_key(settings, vault_client, allow_env_fallback=False, for_cli=False)
        resolved["anthropic_api_key"] = "resolved"

    warnings: list[str] = []
    if settings.db_password_secret_path:
        _resolve_vault_field(
            vault_client,
            settings.db_password_secret_path,
            field_name="password",
            error_message="Database password could not be resolved from Vault.",
            required=True,
        )
        resolved["db_password"] = "resolved"
    else:
        warnings.append("Database password secret path is not configured; compose/dev env-backed DB remains in use.")

    if settings.minio_access_key_secret_path:
        minio_access_key = _resolve_vault_field(
            vault_client,
            settings.minio_access_key_secret_path,
            field_name="access_key",
            error_message="MinIO access key could not be resolved from Vault.",
            required=True,
        )
        settings.minio_access_key = str(minio_access_key)
        resolved["minio_access_key"] = "resolved"
    else:
        warnings.append("MinIO access key secret path is not configured; compose/dev env-backed MinIO remains in use.")

    if settings.minio_secret_key_secret_path:
        minio_secret_key = _resolve_vault_field(
            vault_client,
            settings.minio_secret_key_secret_path,
            field_name="secret_key",
            error_message="MinIO secret key could not be resolved from Vault.",
            required=True,
        )
        settings.minio_secret_key = str(minio_secret_key)
        resolved["minio_secret_key"] = "resolved"
    else:
        warnings.append("MinIO secret key secret path is not configured; compose/dev env-backed MinIO remains in use.")

    resolved["warnings"] = warnings
    return resolved


def validate_eval_thresholds(path: Path) -> None:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required_sections = {
        "classification": ["min_accuracy", "min_macro_f1"],
        "rag_retrieval": ["min_hit_at_5", "min_mrr_at_10"],
        "rag_generation": [
            "min_answer_relevancy",
            "min_faithfulness",
            "min_citation_coverage",
            "min_groundedness_pass_rate",
        ],
    }
    for section, keys in required_sections.items():
        section_payload = payload.get(section)
        if not isinstance(section_payload, dict):
            raise StartupValidationError(f"Eval thresholds are missing required section: {section}")
        for key in keys:
            value = section_payload.get(key)
            if not isinstance(value, (int, float)) or float(value) <= 0:
                raise StartupValidationError(f"Eval threshold {section}.{key} must be greater than zero.")


def validate_required_reports(*, repo_root: Path, env: str, warnings: list[str]) -> None:
    required_paths = [
        repo_root / "reports/eval_report.json",
        repo_root / "reports/rag_generation_eval_report.json",
    ]
    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if not missing:
        return
    if env == "development":
        warnings.append(f"Missing report files: {', '.join(missing)}")
        return
    raise StartupValidationError(f"Required report files are missing: {', '.join(missing)}")


def validate_model_server_health(settings: Settings) -> None:
    if not settings.require_model_server_health:
        return
    try:
        response = httpx.get(f"{settings.model_server_url.rstrip('/')}/health", timeout=3.0)
    except Exception as exc:
        raise StartupValidationError("Model-server health check failed.") from exc
    if response.status_code != 200:
        raise StartupValidationError("Model-server health check failed.")


def validate_tracing_policy(settings: Settings) -> None:
    if settings.require_tracing and not settings.tracing_backend_url:
        raise StartupValidationError("Tracing is required but tracing backend config is missing.")


def _resolve_vault_field(
    vault_client: VaultClient,
    path: str | None,
    *,
    field_name: str,
    error_message: str,
    required: bool,
) -> str | None:
    if not path:
        if required:
            raise StartupValidationError(error_message)
        return None
    try:
        payload = vault_client.read_kv_v2_secret(path)
    except VaultSecretError as exc:
        raise StartupValidationError(error_message) from exc
    if not payload:
        raise StartupValidationError(error_message)
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise StartupValidationError(error_message)
    return value.strip()
