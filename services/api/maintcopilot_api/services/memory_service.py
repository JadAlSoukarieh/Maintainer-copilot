from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from maintcopilot_api.domain.errors import DependencyUnavailableError
from maintcopilot_api.domain.memory import MemoryWriteRequest, MemoryWriteResponse
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.embeddings import EmbeddingUnavailableError, LocalSentenceTransformerEmbedder
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.repositories.memory_repository import MemoryRepository


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepository,
        session: Session,
        *,
        settings: Settings | None = None,
        embedder: LocalSentenceTransformerEmbedder | None = None,
    ) -> None:
        self._repository = repository
        self._session = session
        self._settings = settings
        self._embedder = embedder

    def create(self, payload: MemoryWriteRequest) -> MemoryWriteResponse:
        embedding = self._embed_text(str(redact(payload.content)))
        memory_id = self._repository.create_memory(
            user_id=payload.user_id,
            content=str(redact(payload.content)),
            conversation_id=payload.conversation_id,
            metadata=payload.metadata,
            embedding=embedding,
        )
        self._session.commit()
        log_with_context(
            logging.getLogger("app.audit"),
            "info",
            "audit.memory.write",
            memory_id=str(memory_id),
            user_id=payload.user_id,
            conversation_id=payload.conversation_id,
        )
        return MemoryWriteResponse(memory_id=memory_id, status="stored")

    def list_memories(self, *, user_id: str | None = None, limit: int = 100) -> list[dict]:
        return [redact(row) for row in self._repository.list_memories(user_id=user_id, limit=limit)]

    def search_memories(
        self,
        *,
        query_text: str,
        user_id: str | None = None,
        limit: int = 100,
        mode: str = "hybrid",
    ) -> dict:
        query_embedding = None
        fallback_reason = None
        try:
            query_embedding = self._embed_text(query_text, strict=False)
        except DependencyUnavailableError:
            if mode in {"vector", "hybrid"}:
                fallback_reason = "vector_unavailable"
        result = self._repository.search_memories(
            query_text=query_text,
            user_id=user_id,
            limit=limit,
            mode=mode,
            query_embedding=query_embedding,
        )
        if fallback_reason and not result.get("fallback_reason"):
            result["fallback_reason"] = fallback_reason
        result["items"] = [redact(row) for row in result.get("items", [])]
        return result

    def vector_status(self) -> dict[str, object]:
        available = self._embedder.is_available() if self._embedder is not None else False
        return {
            "vector_available": available,
            "fallback_allowed": bool(self._settings.allow_memory_text_fallback) if self._settings else True,
            "embedding_model": self._settings.memory_embedding_model if self._settings else None,
            "embedding_dimension": self._settings.memory_embedding_dimension if self._settings else None,
        }

    def _embed_text(self, text: str, *, strict: bool = True) -> list[float] | None:
        if self._embedder is None:
            if strict and self._settings and self._settings.require_memory_vector:
                raise DependencyUnavailableError("Vector memory is required but the embedder is not configured.")
            return None
        try:
            return self._embedder.embed_text(text)
        except EmbeddingUnavailableError as exc:
            if self._settings and self._settings.require_memory_vector and strict:
                raise DependencyUnavailableError("Vector memory is required but embeddings are unavailable.") from exc
            if self._settings and not self._settings.allow_memory_text_fallback and strict:
                raise DependencyUnavailableError("Vector memory is unavailable and text fallback is disabled.") from exc
            return None
