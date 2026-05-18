from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session

from maintcopilot_api.repositories.base import memories


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_memory(
        self,
        *,
        user_id: str,
        content: str,
        conversation_id: str | None,
        metadata: dict[str, Any],
    ) -> str:
        memory_id = str(uuid.uuid4())
        self._session.execute(
            insert(memories).values(
                id=memory_id,
                user_id=user_id,
                content=content,
                conversation_id=conversation_id,
                metadata=metadata,
            )
        )
        return memory_id
