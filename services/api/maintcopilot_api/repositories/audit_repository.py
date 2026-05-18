from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from maintcopilot_api.repositories.base import audit_logs


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_event(self, *, event_type: str, actor_id: str | None, payload: dict[str, Any]) -> str:
        audit_id = str(uuid.uuid4())
        self._session.execute(
            insert(audit_logs).values(
                id=audit_id,
                event_type=event_type,
                actor_id=actor_id,
                payload=payload,
            )
        )
        return audit_id

    def list_events(self) -> list[dict[str, Any]]:
        rows = self._session.execute(select(audit_logs)).mappings().all()
        return [dict(row) for row in rows]
