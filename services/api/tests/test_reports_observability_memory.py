from __future__ import annotations

from types import SimpleNamespace

from maintcopilot_api.api.routes.chat import chat_memory
from maintcopilot_api.api.routes.observability import recent_observability_events
from maintcopilot_api.api.routes.reports import reports_summary
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.repositories.memory_repository import MemoryRepository
from maintcopilot_api.services.memory_service import MemoryService
from maintcopilot_api.services.short_term_memory import InMemoryShortTermMemoryStore


def test_reports_summary_returns_project_metrics() -> None:
    summary = reports_summary()

    assert summary["classifier"]["selected"]
    assert "rag_retrieval" in summary
    assert summary["notes"]["long_term_memory"] == "pgvector_episodic_with_text_fallback"


def test_recent_events_are_redacted() -> None:
    import logging

    log_with_context(logging.getLogger("test"), "info", "chat.tool.selected", token="sk-test-secret")

    response = recent_observability_events()
    rendered = str(response["items"])
    assert "sk-test-secret" not in rendered
    assert "[REDACTED]" in rendered


def test_recent_events_support_filters() -> None:
    import logging

    log_with_context(logging.getLogger("test"), "info", "chat.tool.selected", marker="one")
    log_with_context(logging.getLogger("test"), "info", "memory.write", marker="two")

    response = recent_observability_events(limit=10, event_type="memory.write")

    assert response["items"]
    assert all(item["event"] == "memory.write" for item in response["items"])


def test_chat_memory_endpoint_returns_redacted_short_term_events() -> None:
    store = InMemoryShortTermMemoryStore()
    store.append(conversation_id="conv-1", event={"message": "token sk-test-secret"})
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(in_memory_short_term_memory=store)))

    response = chat_memory(
        "conv-1",
        request,
        settings=Settings(require_vault=False, allow_in_memory_memory=True),
        current_user=None,
    )

    rendered = str(response["items"])
    assert "sk-test-secret" not in rendered
    assert "[REDACTED]" in rendered


def test_memory_service_lists_and_searches_redacted_memories(session) -> None:
    service = MemoryService(repository=MemoryRepository(session=session), session=session)
    service._repository.create_memory(
        user_id="user-1",
        content="Remember token sk-test-secret",
        conversation_id="conv-1",
        metadata={"source": "chat.write_memory"},
    )
    session.commit()

    listed = service.list_memories(user_id="user-1")
    searched = service.search_memories(query_text="Remember", user_id="user-1")

    assert listed
    assert searched["items"]
    assert "sk-test-secret" not in str(listed)
    assert "[REDACTED]" in str(listed)


def test_memory_service_embeds_when_available(session) -> None:
    class FakeEmbedder:
        def embed_text(self, text: str) -> list[float]:
            assert "[REDACTED]" in text
            return [0.1, 0.2, 0.3]

        def is_available(self) -> bool:
            return True

    service = MemoryService(
        repository=MemoryRepository(session=session),
        session=session,
        settings=Settings(require_vault=False, require_memory_vector=False),
        embedder=FakeEmbedder(),
    )
    response = service.create(
        SimpleNamespace(user_id="user-1", content="Remember sk-test-secret", conversation_id="conv-1", metadata={"source": "chat.write_memory"})
    )

    stored = service.list_memories(user_id="user-1")
    assert response.status == "stored"
    assert stored


def test_memory_service_emits_audit_log_after_write(session, monkeypatch) -> None:
    import maintcopilot_api.services.memory_service as memory_service_module

    captured = {}

    def fake_log_with_context(logger, level, message, **fields):
        captured.update({"level": level, "message": message, "fields": fields})

    monkeypatch.setattr(memory_service_module, "log_with_context", fake_log_with_context)
    service = MemoryService(
        repository=MemoryRepository(session=session),
        session=session,
        settings=Settings(require_vault=False, require_memory_vector=False),
    )

    response = service.create(
        SimpleNamespace(
            user_id="user-1",
            content="Remember sk-test-secret",
            conversation_id="conv-1",
            metadata={"source": "chat.write_memory"},
        )
    )

    assert response.status == "stored"
    assert captured["message"] == "audit.memory.write"
    assert captured["fields"]["memory_id"] == response.memory_id
    assert captured["fields"]["user_id"] == "user-1"
    assert captured["fields"]["conversation_id"] == "conv-1"


def test_memory_search_reports_vector_fallback(session) -> None:
    service = MemoryService(
        repository=MemoryRepository(session=session),
        session=session,
        settings=Settings(require_vault=False, require_memory_vector=False, allow_memory_text_fallback=True),
        embedder=None,
    )
    service._repository.create_memory(
        user_id="user-1",
        content="Remember socket cleanup",
        conversation_id="conv-1",
        metadata={"source": "chat.write_memory"},
    )
    session.commit()

    searched = service.search_memories(query_text="socket", user_id="user-1", mode="vector")

    assert searched["effective_mode"] == "text"
    assert searched["fallback_reason"] == "vector_unavailable"
