from __future__ import annotations

from typing import Any

import httpx


class VaultSecretError(RuntimeError):
    pass


class VaultClient:
    def __init__(self, *, addr: str, token: str) -> None:
        self._addr = addr.rstrip("/")
        self._token = token

    def check_health(self) -> bool:
        try:
            response = httpx.get(
                f"{self._addr}/v1/sys/health",
                headers={"X-Vault-Token": self._token},
                timeout=2.0,
            )
            return response.status_code in {200, 429, 472, 473}
        except Exception:
            return False

    def read_kv_v2_secret(self, path: str) -> dict[str, Any] | None:
        secret_path = path.lstrip("/")
        try:
            response = httpx.get(
                f"{self._addr}/v1/{secret_path}",
                headers={"X-Vault-Token": self._token},
                timeout=2.0,
            )
        except Exception as exc:
            raise VaultSecretError("Vault secret lookup failed.") from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise VaultSecretError("Vault secret lookup failed.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise VaultSecretError("Vault secret response was not valid JSON.") from exc

        data = payload.get("data")
        if not isinstance(data, dict):
            raise VaultSecretError("Vault secret response was missing data.")

        inner_data = data.get("data")
        if not isinstance(inner_data, dict):
            raise VaultSecretError("Vault secret response was missing KV-v2 payload.")

        return inner_data

    def write_kv_v2_secret(self, path: str, payload: dict[str, Any]) -> None:
        secret_path = path.lstrip("/")
        try:
            response = httpx.post(
                f"{self._addr}/v1/{secret_path}",
                headers={"X-Vault-Token": self._token},
                json={"data": payload},
                timeout=2.0,
            )
        except Exception as exc:
            raise VaultSecretError("Vault secret write failed.") from exc
        if response.status_code not in {200, 204}:
            raise VaultSecretError("Vault secret write failed.")
