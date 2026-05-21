from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from maintcopilot_api.domain.chat import ChatContext, ChatRequest
from maintcopilot_api.domain.rag import RagAnswerRequest
from maintcopilot_api.infra import tracing as tracing_module
from maintcopilot_api.services.llm_chat_service import LLMChatService
from maintcopilot_api.services.rag.rag_service import RagService
from maintcopilot_api.services.tools import ToolExecutor


class FakeSpan:
    def __init__(self, name: str, collector: list[str]) -> None:
        self.name = name
        self.collector = collector

    def __enter__(self):
        self.collector.append(self.name)
        return self

    def __exit__(self, *_):
        return False

    def set_attribute(self, *_args, **_kwargs) -> None:
        return None

    def record_exception(self, *_args, **_kwargs) -> None:
        return None


class FakeTracer:
    def __init__(self, collector: list[str]) -> None:
        self.collector = collector

    def start_as_current_span(self, name: str, **_kwargs):
        return FakeSpan(name, self.collector)


def test_configure_tracing_without_exporter_initializes(monkeypatch) -> None:
    provider_calls = []

    class FakeProvider:
        def __init__(self, resource=None):
            self.resource = resource
            self.processors = []

        def add_span_processor(self, processor) -> None:
            self.processors.append(processor)

    monkeypatch.setattr(tracing_module, "_tracer_initialized", False)
    monkeypatch.setattr(tracing_module, "TracerProvider", FakeProvider)
    monkeypatch.setattr(tracing_module, "BatchSpanProcessor", lambda exporter: ("processor", exporter))
    monkeypatch.setattr(tracing_module, "ConsoleSpanExporter", lambda: "console-exporter")
    monkeypatch.setattr(tracing_module.trace, "set_tracer_provider", lambda provider: provider_calls.append(provider))

    tracing_module.configure_tracing(service_name="test-service", otlp_endpoint=None)

    assert provider_calls


def test_recent_events_request_id_filter_works() -> None:
    from maintcopilot_api.api.routes.observability import recent_observability_events
    from maintcopilot_api.infra.logging import log_with_context

    token = tracing_module.request_id_var.set("req-filter-1")
    try:
        log_with_context(__import__("logging").getLogger("test"), "info", "chat.tool.selected", secret="sk-test-secret")
    finally:
        tracing_module.request_id_var.reset(token)

    response = recent_observability_events(limit=10, request_id="req-filter-1")
    assert response["items"]
    assert all(item["request_id"] == "req-filter-1" for item in response["items"])
    assert "sk-test-secret" not in str(response["items"])


def test_llm_and_tool_and_rag_paths_create_spans(monkeypatch, tmp_path: Path) -> None:
    span_names: list[str] = []
    fake_tracer = FakeTracer(span_names)

    import maintcopilot_api.services.llm_chat_service as llm_module
    import maintcopilot_api.services.tools as tools_module
    import maintcopilot_api.services.rag.rag_service as rag_module

    monkeypatch.setattr(llm_module, "get_tracer", lambda: fake_tracer)
    monkeypatch.setattr(tools_module, "get_tracer", lambda: fake_tracer)
    monkeypatch.setattr(rag_module, "get_tracer", lambda: fake_tracer)

    class FakeMessageResponse:
        def __init__(self, content):
            self.content = content
            self.usage = SimpleNamespace(input_tokens=1, output_tokens=1)

    class FakeMessages:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return FakeMessageResponse([SimpleNamespace(type="tool_use", name="rag_answer", input={"question": "How do I debug memory leaks?"}, id="tool-1")])
            return FakeMessageResponse([SimpleNamespace(text="Final grounded answer")])

    class FakeAnthropicClient:
        def __init__(self) -> None:
            self.messages = FakeMessages()

    prompt_path = tmp_path / "chat_system.md"
    prompt_path.write_text("System prompt", encoding="utf-8")
    llm = LLMChatService(
        settings=SimpleNamespace(anthropic_model_name="fake-model", chat_allow_env_key_fallback=False),
        vault_client=None,
        prompt_path=prompt_path,
        anthropic_client=FakeAnthropicClient(),
    )
    payload = ChatRequest(conversation_id=None, message="How do I debug memory leaks?", context=ChatContext(), use_llm=True)
    selection = llm.select_tool(payload)
    llm.final_response(payload=payload, selection=selection, compacted_tool_result={"answer": "Answer", "citations": []})

    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(
        json.dumps(
            {
                "chunk_id": "doc-http-001",
                "source_type": "doc",
                "source_id": "http-1",
                "title": "http",
                "url": "",
                "text": "Document: http\nSection path: HTTP\n\nThe docs explain request cleanup.",
                "metadata": {
                    "repo": "nodejs/node",
                    "source_split": "docs",
                    "label": None,
                    "issue_number": None,
                    "created_at": None,
                    "closed_at": None,
                    "path": "api/http.md",
                    "section": "HTTP",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()
    np.savez_compressed(embedding_dir / "dense_index.npz", embeddings=np.array([[1.0] * 384], dtype=np.float32))
    (embedding_dir / "chunk_ids.json").write_text(json.dumps(["doc-http-001"]), encoding="utf-8")
    rag_service = RagService(corpus_path=corpus_path, embedding_index_dir=embedding_dir, reranker_model_path=tmp_path / "missing-reranker")
    rag_service.answer_rag_question(RagAnswerRequest(question="What do the http docs say?", retriever="sparse"))

    tool_executor = ToolExecutor(
        model_client=SimpleNamespace(
            classify_issue=lambda title, body: {"label": "bug", "title": title, "body": body},
            extract_entities=lambda title, body: {"entities": []},
            summarize_thread=lambda title, body, max_bullets=5: {"bullets": []},
        ),
        rag_service=rag_service,
        memory_service=SimpleNamespace(create=lambda payload: SimpleNamespace(memory_id="mem-1", status="stored")),
    )
    tool_executor.execute(
        "classify_issue",
        {"title": "Leak", "body": "Body"},
        payload=ChatRequest(conversation_id=None, message="Classify this issue", context=ChatContext(issue_title="Leak", issue_body="Body"), use_llm=False),
        conversation_id="conv-1",
        user_id="user-1",
    )

    assert "llm.select_tool" in span_names
    assert "llm.final_response" in span_names
    assert "rag.retrieve" in span_names
    assert "tool.classify_issue" in span_names
