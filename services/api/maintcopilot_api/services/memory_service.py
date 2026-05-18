from __future__ import annotations

from sqlalchemy.orm import Session

from maintcopilot_api.domain.memory import MemoryWriteRequest, MemoryWriteResponse
from maintcopilot_api.repositories.memory_repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository, session: Session) -> None:
        self._repository = repository
        self._session = session

    def create(self, payload: MemoryWriteRequest) -> MemoryWriteResponse:
        memory_id = self._repository.create_memory(
            user_id=payload.user_id,
            content=payload.content,
            conversation_id=payload.conversation_id,
            metadata=payload.metadata,
        )
        self._session.commit()
        return MemoryWriteResponse(memory_id=memory_id, status="stored")
