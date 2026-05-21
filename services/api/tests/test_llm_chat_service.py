from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from maintcopilot_api.domain.chat import ChatRequest
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.services.llm_chat_service import LLMChatService, ToolSelection


ROOT = Path(__file__).resolve().parents[3]


class _FakeResponse:
    def __init__(self, *blocks: Any) -> None:
        self.content = list(blocks)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    class _Messages:
        def __init__(self, outer: "_FakeClient") -> None:
            self.outer = outer

        def create(self, **kwargs: Any) -> Any:
            self.outer.calls.append(kwargs)
            if len(self.outer.calls) == 1:
                return _FakeResponse(SimpleNamespace(type="tool_use", name="rag_answer", input={"question": "q"}, id="tool-1"))
            return _FakeResponse(SimpleNamespace(type="text", text="grounded final answer"))

    @property
    def messages(self) -> "_FakeClient._Messages":
        return self._Messages(self)


def test_llm_final_response_compacts_rag_tool_result_and_includes_requirements() -> None:
    client = _FakeClient()
    service = LLMChatService(
        settings=Settings(require_vault=False, anthropic_model_name="fake-model"),
        vault_client=None,
        prompt_path=ROOT / "prompts" / "chat_system.md",
        anthropic_client=client,
    )
    payload = ChatRequest(message="How do I debug a memory leak in https request?", use_llm=True)
    selection = service.select_tool(payload)
    text = service.final_response(
        payload=payload,
        selection=selection,
        compacted_tool_result={
            "answer": "Based on the local Node.js knowledge base, related issue evidence points to similar symptoms.",
            "citations": [
                {"title": "Issue 1", "source_type": "resolved_issue", "chunk_id": "x", "text_excerpt": "a" * 800}
            ],
        },
    )

    assert text == "grounded final answer"
    tool_result_message = client.calls[1]["messages"][2]["content"][0]["content"]
    payload_json = json.loads(tool_result_message)
    assert payload_json["tool_result"]["citations"][0]["text_excerpt"] == "a" * 800
    assert "Do not invent fixes or root causes." in payload_json["response_requirements"]


def test_llm_system_prompt_contains_untrusted_context_warning() -> None:
    prompt = (ROOT / "prompts" / "chat_system.md").read_text(encoding="utf-8")

    assert "untrusted context" in prompt
    assert "Do not invent fixes" in prompt
