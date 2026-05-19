from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from maintcopilot_api.domain.chat import ChatRequest, ChatToolName
from maintcopilot_api.domain.memory import MemoryWriteRequest
from maintcopilot_api.domain.rag import RagAnswerRequest
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.infra.model_client import ModelClientError, ModelServerClient
from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.services.memory_service import MemoryService
from maintcopilot_api.services.rag.rag_service import RagService
from maintcopilot_api.services.tool_router import has_explicit_memory_intent


class ToolInputValidationError(RuntimeError):
    pass


class ToolFailureError(RuntimeError):
    pass


class ToolExecutor:
    def __init__(
        self,
        *,
        model_client: ModelServerClient,
        rag_service: RagService,
        memory_service: MemoryService,
        audit_repository: AuditRepository | None = None,
        session: Session | None = None,
    ) -> None:
        self._model_client = model_client
        self._rag_service = rag_service
        self._memory_service = memory_service
        self._audit_repository = audit_repository
        self._session = session
        self.executed_tools: list[ChatToolName] = []

    def execute(
        self,
        tool_name: ChatToolName,
        tool_input: dict[str, Any],
        *,
        payload: ChatRequest,
        conversation_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        self.executed_tools.append(tool_name)
        if tool_name == "classify_issue":
            result = self._classify_issue(tool_input, payload)
        elif tool_name == "extract_entities":
            result = self._extract_entities(tool_input, payload)
        elif tool_name == "summarize_thread":
            result = self._summarize_thread(tool_input, payload)
        elif tool_name == "rag_answer":
            result = self._rag_answer(tool_input, payload)
        elif tool_name == "write_memory":
            result = self._write_memory(tool_input, payload=payload, conversation_id=conversation_id, user_id=user_id)
        elif tool_name == "none":
            result = {"status": "no_tool_selected"}
        else:
            raise ToolInputValidationError(f"Unsupported tool: {tool_name}")
        log_with_context(logging.getLogger("app.chat"), "info", "chat.tool.completed", selected_tool=tool_name)
        return result

    def _classify_issue(self, tool_input: dict[str, Any], payload: ChatRequest) -> dict[str, Any]:
        title, body = _issue_title_body(tool_input, payload)
        try:
            return self._model_client.classify_issue(title=title, body=body)
        except ModelClientError as exc:
            raise ToolFailureError("Issue classification tool is unavailable.") from exc

    def _extract_entities(self, tool_input: dict[str, Any], payload: ChatRequest) -> dict[str, Any]:
        title, body = _issue_title_body(tool_input, payload)
        try:
            return self._model_client.extract_entities(title=title, body=body)
        except ModelClientError as exc:
            raise ToolFailureError("Entity extraction tool is unavailable.") from exc

    def _summarize_thread(self, tool_input: dict[str, Any], payload: ChatRequest) -> dict[str, Any]:
        title, body = _issue_title_body(tool_input, payload)
        max_bullets = min(int(tool_input.get("max_bullets") or 5), 5)
        try:
            return self._model_client.summarize_thread(title=title, body=body, max_bullets=max_bullets)
        except ModelClientError as exc:
            raise ToolFailureError("Summarization tool is unavailable.") from exc

    def _rag_answer(self, tool_input: dict[str, Any], payload: ChatRequest) -> dict[str, Any]:
        question_source = tool_input.get("question") if "question" in tool_input else payload.message
        question = str(question_source or "").strip()
        if not question:
            raise ToolInputValidationError("rag_answer requires a non-empty question.")
        result = self._rag_service.answer_rag_question(
            RagAnswerRequest(
                question=question,
                top_k=5,
                retriever="hybrid",
                alpha=0.5,
                query_rewrite=True,
                metadata_boost=True,
            )
        )
        return result.model_dump()

    def _write_memory(
        self,
        tool_input: dict[str, Any],
        *,
        payload: ChatRequest,
        conversation_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        if not has_explicit_memory_intent(payload.message):
            raise ToolInputValidationError("write_memory requires an explicit remember/save/note request.")
        memory_text = str(tool_input.get("memory_text") or payload.message).strip()
        if not memory_text:
            raise ToolInputValidationError("write_memory requires non-empty memory_text.")
        response = self._memory_service.create(
            MemoryWriteRequest(
                user_id=user_id,
                content=str(redact(memory_text)),
                conversation_id=conversation_id,
                metadata={
                    "source": "chat.write_memory",
                    "memory_type": str(tool_input.get("memory_type") or "episodic"),
                },
            )
        )
        if self._audit_repository is not None:
            self._audit_repository.create_event(
                event_type="memory.write",
                actor_id=user_id,
                payload={"conversation_id": conversation_id, "memory_id": response.memory_id, "source": "chat.write_memory"},
            )
            if self._session is not None:
                self._session.commit()
        log_with_context(logging.getLogger("app.chat"), "info", "memory.write", conversation_id=conversation_id)
        return {"memory_id": response.memory_id, "status": response.status, "source": "chat.write_memory"}


def compact_tool_result(tool_name: ChatToolName, result: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "rag_answer":
        compacted = dict(result)
        citations = []
        for citation in list(compacted.get("citations") or [])[:5]:
            item = dict(citation)
            item["text_excerpt"] = _truncate(str(item.get("text_excerpt") or ""), 800)
            citations.append(item)
        compacted["citations"] = citations
        return compacted
    if tool_name == "extract_entities":
        compacted = dict(result)
        compacted["entities"] = list(compacted.get("entities") or [])[:20]
        return compacted
    if tool_name == "summarize_thread":
        compacted = dict(result)
        compacted["bullets"] = list(compacted.get("bullets") or [])[:5]
        return compacted
    if tool_name == "classify_issue":
        return {
            key: result[key]
            for key in ("label", "confidence", "top_probabilities", "model_name", "model_type")
            if key in result
        }
    return dict(result)


def _issue_title_body(tool_input: dict[str, Any], payload: ChatRequest) -> tuple[str, str]:
    title = str(tool_input.get("title") or payload.context.issue_title or "").strip()
    body = str(tool_input.get("body") or payload.context.issue_body or "").strip()
    if not title or not body:
        raise ToolInputValidationError("This tool requires issue_title and issue_body.")
    return title, body


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."
