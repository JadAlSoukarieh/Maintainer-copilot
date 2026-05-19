from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maintcopilot_api.domain.chat import ChatRequest, ChatToolName
from maintcopilot_api.infra.anthropic_client import AnthropicKeyResolutionError, AnthropicRequestError, resolve_anthropic_api_key
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.vault import VaultClient


class LLMChatError(RuntimeError):
    pass


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
            raise LLMChatError("Claude chat tool selection failed.") from exc
        selection = _parse_tool_selection(response)
        if selection is None:
            return ToolSelection(selected_tool="none", tool_input={}, direct_message=_text_from_response(response))
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
                                "content": json.dumps(compacted_tool_result, default=str),
                            }
                        ],
                    },
                ],
            )
        except Exception as exc:
            raise LLMChatError("Claude chat final response failed.") from exc
        text = _text_from_response(response)
        return text or _fallback_final_text(selection.selected_tool, compacted_tool_result)

    def _build_client(self):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise AnthropicRequestError("The anthropic SDK is not installed.") from exc
        try:
            self._api_key = resolve_anthropic_api_key(self._settings, self._vault_client, allow_env_fallback=False, for_cli=False)
        except AnthropicKeyResolutionError as exc:
            raise LLMChatError("Claude API key could not be resolved.") from exc
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
