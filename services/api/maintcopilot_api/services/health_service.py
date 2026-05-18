from __future__ import annotations

from sqlalchemy import text

from maintcopilot_api.domain.errors import DependencyUnavailableError
from maintcopilot_api.infra.vault import VaultClient


class HealthService:
    def __init__(self, session_factory, vault_client: VaultClient, require_vault: bool) -> None:
        self._session_factory = session_factory
        self._vault_client = vault_client
        self._require_vault = require_vault

    def ready(self) -> dict[str, object]:
        db_ok = self._check_database()
        vault_required = self._require_vault
        vault_ok = (not vault_required) or self._vault_client.check_health()
        if not db_ok:
            raise DependencyUnavailableError("Database is not ready.")
        if not vault_ok:
            raise DependencyUnavailableError("Vault is not ready.")
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "vault": "ok" if vault_required else "skipped",
            },
        }

    def _check_database(self) -> bool:
        try:
            with self._session_factory() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
