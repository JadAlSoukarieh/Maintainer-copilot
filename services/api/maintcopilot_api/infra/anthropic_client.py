from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.vault import VaultClient, VaultSecretError


class AnthropicKeyResolutionError(RuntimeError):
    pass


class AnthropicRequestError(RuntimeError):
    pass


@dataclass(slots=True)
class AnthropicClassificationResponse:
    raw_output: str
    input_tokens: int
    output_tokens: int
    model_name: str


@dataclass(slots=True)
class AnthropicKeyResolution:
    api_key: str | None
    key_source: str
    key_present: bool
    key_length: int
    prefix_ok: bool


PLACEHOLDER_ANTHROPIC_KEY = "placeholder-not-required"


def resolve_anthropic_api_key_details(
    settings: Settings,
    vault_client: VaultClient | None,
    *,
    allow_env_fallback: bool = False,
    for_cli: bool = False,
) -> AnthropicKeyResolution:
    del for_cli
    env_key = _normalize_key(os.getenv("ANTHROPIC_API_KEY"))
    env_result = _resolution("env", env_key)

    # Local/dev mode should prefer the shell/.env.local key over any demo Vault placeholder.
    if not settings.require_vault and env_key:
        return env_result

    vault_key = ""
    secret_path = settings.anthropic_api_key_secret_path
    if secret_path and vault_client is not None:
        try:
            payload = vault_client.read_kv_v2_secret(secret_path)
        except VaultSecretError as exc:
            if settings.require_vault and not (allow_env_fallback and env_key):
                raise AnthropicKeyResolutionError("Anthropic API key could not be resolved from Vault.") from exc
            payload = None

        if payload:
            vault_key = _normalize_key(payload.get("api_key"))
            if vault_key and not _is_placeholder_key(vault_key):
                return _resolution("vault", vault_key)
    elif settings.require_vault and not (allow_env_fallback and env_key):
        raise AnthropicKeyResolutionError("Anthropic API key secret path is not configured.")

    if env_key and (allow_env_fallback or not settings.require_vault):
        return env_result

    if _is_placeholder_key(vault_key):
        return _resolution("placeholder", None)
    return _resolution("missing", None)


def resolve_anthropic_api_key(
    settings: Settings,
    vault_client: VaultClient | None,
    *,
    allow_env_fallback: bool = False,
    for_cli: bool = False,
) -> str:
    resolution = resolve_anthropic_api_key_details(
        settings,
        vault_client,
        allow_env_fallback=allow_env_fallback,
        for_cli=for_cli,
    )
    if resolution.api_key:
        return resolution.api_key
    if resolution.key_source == "placeholder":
        raise AnthropicKeyResolutionError(
            "Anthropic API key is still using the local demo placeholder. Configure Vault or set ANTHROPIC_API_KEY."
        )
    raise AnthropicKeyResolutionError(
        "Anthropic API key is not configured. Configure Vault or set ANTHROPIC_API_KEY for local development."
    )


def read_vault_anthropic_key_metadata(settings: Settings, vault_client: VaultClient | None) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    secret_path = settings.anthropic_api_key_secret_path
    if secret_path and vault_client is not None:
        try:
            payload = vault_client.read_kv_v2_secret(secret_path)
        except VaultSecretError:
            payload = None

    vault_key = _normalize_key((payload or {}).get("api_key"))
    return {
        "vault_key_present": bool(vault_key),
        "vault_key_length": len(vault_key),
        "vault_prefix_ok": vault_key.startswith("sk-ant-"),
        "vault_placeholder_detected": _is_placeholder_key(vault_key),
    }


def _normalize_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _is_placeholder_key(value: str) -> bool:
    return value == PLACEHOLDER_ANTHROPIC_KEY


def _resolution(key_source: str, api_key: str | None) -> AnthropicKeyResolution:
    normalized_key = _normalize_key(api_key)
    return AnthropicKeyResolution(
        api_key=normalized_key or None,
        key_source=key_source,
        key_present=bool(normalized_key),
        key_length=len(normalized_key),
        prefix_ok=normalized_key.startswith("sk-ant-"),
    )


class AnthropicClassifierClient:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
        sleep_between_calls_seconds: float = 0.15,
    ) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise AnthropicRequestError("The anthropic SDK is not installed.") from exc

        self._client = Anthropic(api_key=api_key)
        self._model_name = model_name
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._sleep_between_calls_seconds = sleep_between_calls_seconds

    def classify(self, prompt: str, *, max_tokens: int = 50, temperature: float = 0.0) -> AnthropicClassificationResponse:
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=self._model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                text_blocks: list[str] = []
                for block in getattr(response, "content", []):
                    text_value = getattr(block, "text", None)
                    if isinstance(text_value, str):
                        text_blocks.append(text_value)
                usage = getattr(response, "usage", None)
                input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
                if self._sleep_between_calls_seconds > 0:
                    time.sleep(self._sleep_between_calls_seconds)
                return AnthropicClassificationResponse(
                    raw_output="".join(text_blocks).strip(),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model_name=self._model_name,
                )
            except Exception as exc:  # pragma: no cover - concrete SDK failures depend on installed version
                last_error = exc
                if attempt >= self._max_retries or not _is_transient_error(exc):
                    break
                time.sleep(self._base_backoff_seconds * (2 ** (attempt - 1)))

        raise AnthropicRequestError("Anthropic classification request failed.") from last_error


def _is_transient_error(exc: Exception) -> bool:
    name = exc.__class__.__name__
    if name in {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError"}:
        return True

    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and (status_code == 429 or status_code >= 500):
        return True

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int) and (response_status == 429 or response_status >= 500):
        return True

    return False
