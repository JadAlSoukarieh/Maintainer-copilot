from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import insert, select, text
from sqlalchemy.orm import Session

from maintcopilot_api.repositories.base import conversations, memories


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
        embedding: list[float] | None = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        if conversation_id:
            self._ensure_conversation(conversation_id=conversation_id, user_id=user_id)
        if embedding is not None and self._supports_vector_search():
            self._session.execute(
                text(
                    """
                    INSERT INTO memories (id, conversation_id, user_id, content, metadata, embedding)
                    VALUES (:id, :conversation_id, :user_id, :content, CAST(:metadata AS json), CAST(:embedding AS vector))
                    """
                ),
                {
                    "id": memory_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "content": content,
                    "metadata": json.dumps(metadata),
                    "embedding": _vector_literal(embedding),
                },
            )
            return memory_id
        self._session.execute(
            insert(memories).values(
                id=memory_id,
                user_id=user_id,
                content=content,
                conversation_id=conversation_id,
                metadata=metadata,
                embedding=embedding,
            )
        )
        return memory_id

    def list_memories(self, *, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = select(memories).order_by(memories.c.created_at.desc()).limit(limit)
        if user_id is not None:
            query = query.where(memories.c.user_id == user_id)
        rows = self._session.execute(query).mappings().all()
        return [dict(row) for row in rows]

    def search_memories(
        self,
        *,
        query_text: str,
        user_id: str | None = None,
        limit: int = 100,
        mode: str = "text",
        query_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        if mode == "vector" and self._supports_vector_search() and query_embedding is not None:
            items = self._vector_search(query_embedding=query_embedding, user_id=user_id, limit=limit)
            return {
                "items": items,
                "requested_mode": mode,
                "effective_mode": "vector",
                "vector_available": True,
                "fallback_reason": None,
            }

        if mode == "hybrid" and self._supports_vector_search() and query_embedding is not None:
            text_items = self._text_search(query_text=query_text, user_id=user_id, limit=limit)
            vector_items = self._vector_search(query_embedding=query_embedding, user_id=user_id, limit=limit)
            merged = self._merge_hybrid(text_items=text_items, vector_items=vector_items, limit=limit)
            return {
                "items": merged,
                "requested_mode": mode,
                "effective_mode": "hybrid",
                "vector_available": True,
                "fallback_reason": None,
            }

        fallback_reason = None
        if mode in {"vector", "hybrid"}:
            fallback_reason = "vector_unavailable"
        return {
            "items": self._text_search(query_text=query_text, user_id=user_id, limit=limit),
            "requested_mode": mode,
            "effective_mode": "text",
            "vector_available": self._supports_vector_search(),
            "fallback_reason": fallback_reason,
        }

    def _text_search(self, *, query_text: str, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = select(memories).order_by(memories.c.created_at.desc()).limit(limit)
        if user_id is not None:
            query = query.where(memories.c.user_id == user_id)
        if query_text.strip():
            query = query.where(memories.c.content.ilike(f"%{query_text.strip()}%"))
        rows = self._session.execute(query).mappings().all()
        return [dict(row) for row in rows]

    def _vector_search(
        self,
        *,
        query_embedding: list[float],
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        vector_literal = _vector_literal(query_embedding)
        sql = """
            SELECT id, conversation_id, user_id, content, metadata, embedding, created_at, updated_at,
                   embedding <=> CAST(:embedding AS vector) AS distance
            FROM memories
            WHERE embedding IS NOT NULL
        """
        params: dict[str, Any] = {"embedding": vector_literal, "limit": limit}
        if user_id is not None:
            sql += " AND user_id = :user_id"
            params["user_id"] = user_id
        sql += " ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT :limit"
        rows = self._session.execute(text(sql), params).mappings().all()
        return [dict(row) for row in rows]

    def _supports_vector_search(self) -> bool:
        return bool(self._session.bind and self._session.bind.dialect.name == "postgresql")

    def _ensure_conversation(self, *, conversation_id: str, user_id: str) -> None:
        if self._session.bind and self._session.bind.dialect.name == "postgresql":
            self._session.execute(
                text(
                    """
                    INSERT INTO conversations (id, user_id)
                    VALUES (:id, :user_id)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": conversation_id, "user_id": user_id},
            )
            return
        existing = self._session.execute(select(conversations.c.id).where(conversations.c.id == conversation_id)).scalar_one_or_none()
        if existing is None:
            self._session.execute(insert(conversations).values(id=conversation_id, user_id=user_id))

    @staticmethod
    def _merge_hybrid(
        *,
        text_items: list[dict[str, Any]],
        vector_items: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        combined: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(text_items):
            key = str(item.get("id"))
            entry = combined.setdefault(key, dict(item))
            entry["_hybrid_score"] = entry.get("_hybrid_score", 0.0) + (1.0 / (index + 1))
        for index, item in enumerate(vector_items):
            key = str(item.get("id"))
            entry = combined.setdefault(key, dict(item))
            entry["_hybrid_score"] = entry.get("_hybrid_score", 0.0) + (1.0 / (index + 1))
        return sorted(combined.values(), key=lambda row: float(row.get("_hybrid_score", 0.0)), reverse=True)[:limit]


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
