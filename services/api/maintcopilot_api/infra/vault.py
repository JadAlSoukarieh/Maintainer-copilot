from __future__ import annotations

import httpx


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

