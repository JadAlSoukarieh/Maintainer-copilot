from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maintcopilot_api.domain.chat import ChatRequest, ChatToolName
from maintcopilot_api.infra.anthropic_client import AnthropicRequestError, resolve_anthropic_api_key_details
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.infra.tracing import get_tracer
from maintcopilot_api.infra.vault import VaultClient


class LLMChatError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        reason: str = "llm_unavailable",
        provider_status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.provider_status_code = provider_status_code


@dataclass(slots=True)
class ToolSelection:
    selected_tool: ChatToolName
    tool_input: dict[str, Any]
    direct_message: str | None = None
    tool_use_id: str | None = None


class LLMChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        vault_client: VaultClient | None,
        prompt_path: Path,
        anthropic_client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._vault_client = vault_client
        self._prompt_path = prompt_path
        self._client = anthropic_client
        self._api_key: str | None = None

    def select_tool(self, payload: ChatRequest) -> ToolSelection:
        if self._client is None:
            self._client = self._build_client()
        tracer = get_tracer()
        with tracer.start_as_current_span("llm.select_tool") as span:
            span.set_attribute("llm.model", self._settings.anthropic_model_name)
            span.set_attribute("llm.call_type", "tool_selection")
            try:
                response = self._client.messages.create(
                    model=self._settings.anthropic_model_name,
                    max_tokens=512,
                    temperature=0,
                    system=self._system_prompt(),
                    tools=CHAT_TOOLS,
                    messages=[{"role": "user", "content": _user_payload(payload)}],
                )
            except Exception as exc:
                span.record_exception(exc)
                reason, provider_status_code = _classify_provider_exception(exc)
                raise LLMChatError(
                    "Claude chat tool selection failed.",
                    reason=reason,
                    provider_status_code=provider_status_code,
                ) from exc
            _annotate_usage(span, getattr(response, "usage", None))
            selection = _parse_tool_selection(response)
            if selection is None:
                span.set_attribute("llm.selected_tool", "none")
                return ToolSelection(selected_tool="none", tool_input={}, direct_message=_text_from_response(response))
            span.set_attribute("llm.selected_tool", selection.selected_tool)
            return selection

    def final_response(
        self,
        *,
        payload: ChatRequest,
        selection: ToolSelection,
        compacted_tool_result: dict[str, Any],
    ) -> str:
        if self._client is None:
            self._client = self._build_client()
        if not selection.tool_use_id:
            return selection.direct_message or _fallback_final_text(selection.selected_tool, compacted_tool_result)
        assistant_content = [
            {
                "type": "tool_use",
                "id": selection.tool_use_id,
                "name": selection.selected_tool,
                "input": selection.tool_input,
            }
        ]
        tracer = get_tracer()
        with tracer.start_as_current_span("llm.final_response") as span:
            span.set_attribute("llm.model", self._settings.anthropic_model_name)
            span.set_attribute("llm.call_type", "final_response")
            span.set_attribute("llm.selected_tool", selection.selected_tool)
            try:
                response = self._client.messages.create(
                    model=self._settings.anthropic_model_name,
                    max_tokens=512,
                    temperature=0,
                    system=self._system_prompt(),
                    messages=[
                        {"role": "user", "content": _user_payload(payload)},
                        {"role": "assistant", "content": assistant_content},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": selection.tool_use_id,
                                    "content": json.dumps(
                                        {
                                            "tool_result": compacted_tool_result,
                                            "response_requirements": [
                                                "Use the retrieved citations as evidence.",
                                                "Do not invent fixes or root causes.",
                                                "If the evidence is related but inconclusive, say so.",
                                                "Keep chunk IDs and raw tool metadata out of the main prose answer.",
                                            ],
                                        },
                                        default=str,
                                    ),
                                }
                            ],
                        },
                    ],
                )
            except Exception as exc:
                span.record_exception(exc)
                reason, provider_status_code = _classify_provider_exception(exc)
                raise LLMChatError(
                    "Claude chat final response failed.",
                    reason=reason,
                    provider_status_code=provider_status_code,
                ) from exc
            _annotate_usage(span, getattr(response, "usage", None))
            text = _text_from_response(response)
            return text or _fallback_final_text(selection.selected_tool, compacted_tool_result)

    def _build_client(self):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMChatError("The anthropic SDK is not installed.", reason="llm_unavailable") from exc
        resolution = resolve_anthropic_api_key_details(
            self._settings,
            self._vault_client,
            allow_env_fallback=self._settings.chat_allow_env_key_fallback,
            for_cli=False,
        )
        log_with_context(
            logging.getLogger("app.llm"),
            "info",
            "anthropic.key_resolved",
            key_source=resolution.key_source,
            key_present=resolution.key_present,
            key_length=resolution.key_length,
            prefix_ok=resolution.prefix_ok,
        )
        if not resolution.api_key:
            raise LLMChatError("Claude API key could not be resolved.", reason="llm_missing_key")
        self._api_key = resolution.api_key
        return Anthropic(api_key=self._api_key)

    def _system_prompt(self) -> str:
        return self._prompt_path.read_text(encoding="utf-8")


CHAT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "classify_issue",
        "description": "Classify a GitHub issue into bug, feature, docs, or question.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"],
        },
    },
    {
        "name": "extract_entities",
        "description": "Extract code-shaped entities from issue text.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"],
        },
    },
    {
        "name": "summarize_thread",
        "description": "Summarize an issue thread extractively.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "max_bullets": {"type": "integer"}},
            "required": ["title", "body"],
        },
    },
    {
        "name": "rag_answer",
        "description": "Answer a factual question using the local Node.js docs/issues RAG corpus.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "write_memory",
        "description": "Write long-term memory only when the user explicitly asks to remember, save, or note something.",
        "input_schema": {
            "type": "object",
            "properties": {"memory_text": {"type": "string"}, "memory_type": {"type": "string"}},
            "required": ["memory_text"],
        },
    },
]


def _user_payload(payload: ChatRequest) -> str:
    return json.dumps(
        {
            "message": payload.message,
            "context": payload.context.model_dump(),
        },
        default=str,
    )


def _parse_tool_selection(response: Any) -> ToolSelection | None:
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "tool_use":
            name = str(getattr(block, "name", "none"))
            if name not in {tool["name"] for tool in CHAT_TOOLS}:
                name = "none"
            tool_input = getattr(block, "input", {}) or {}
            if not isinstance(tool_input, dict):
                tool_input = {}
            return ToolSelection(
                selected_tool=name,  # type: ignore[arg-type]
                tool_input=tool_input,
                tool_use_id=str(getattr(block, "id", "") or ""),
            )
    return None


def _text_from_response(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts).strip()


def _annotate_usage(span: Any, usage: Any) -> None:
    if usage is None:
        return
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is not None:
        span.set_attribute("llm.input_tokens", input_tokens)
    if output_tokens is not None:
        span.set_attribute("llm.output_tokens", output_tokens)


def _fallback_final_text(tool_name: ChatToolName, result: dict[str, Any]) -> str:
    if tool_name == "classify_issue" and "label" in result:
        return f"I classified this issue as {result['label']}."
    if tool_name == "rag_answer" and "answer" in result:
        return str(result["answer"])
    if tool_name == "write_memory":
        return "I saved that memory."
    if tool_name == "extract_entities":
        return "I extracted the code-shaped entities from the issue text."
    if tool_name == "summarize_thread":
        return str(result.get("summary") or "I summarized the issue thread.")
    return "I handled the request with the selected tool."


def _classify_provider_exception(exc: Exception) -> tuple[str, int | None]:
    status_code = getattr(exc, "status_code", None)
    if not isinstance(status_code, int):
        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            status_code = response_status

    if status_code == 401:
        return "llm_auth_failed", status_code

    name = exc.__class__.__name__
    if name in {"APITimeoutError", "TimeoutException"} or isinstance(exc, TimeoutError):
        return "llm_timeout", status_code if isinstance(status_code, int) else None

    return "llm_unavailable", status_code if isinstance(status_code, int) else None
