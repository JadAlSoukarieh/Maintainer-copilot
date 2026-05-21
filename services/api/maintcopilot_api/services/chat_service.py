from __future__ import annotations

import logging
import uuid
from typing import Any

from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.chat import ChatMemoryInfo, ChatRequest, ChatResponse, ChatToolName
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.services.llm_chat_service import LLMChatError, LLMChatService, ToolSelection
from maintcopilot_api.services.short_term_memory import ShortTermMemoryStore
from maintcopilot_api.services.tool_router import route_tool
from maintcopilot_api.services.tools import ToolExecutor, ToolFailureError, ToolInputValidationError, compact_tool_result


class ChatService:
    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        short_term_memory: ShortTermMemoryStore,
        settings: Settings,
        llm_chat_service: LLMChatService | None = None,
    ) -> None:
        self._tool_executor = tool_executor
        self._short_term_memory = short_term_memory
        self._settings = settings
        self._llm_chat_service = llm_chat_service

    def chat(
        self,
        payload: ChatRequest,
        *,
        request_id: str,
        trace_id: str,
        current_user: UserRead | None = None,
    ) -> ChatResponse:
        conversation_id = payload.conversation_id or str(uuid.uuid4())
        user_id = current_user.id if current_user is not None else "anonymous"
        memory_writes: list[dict[str, Any]] = []
        logger = logging.getLogger("app.chat")
        log_with_context(logger, "info", "chat.message.received", conversation_id=conversation_id)
        self._short_term_memory.append(
            conversation_id=conversation_id,
            event={"role": "user", "message": payload.message, "context": payload.context.model_dump(), "request_id": request_id},
        )

        requested_use_llm = payload.use_llm if payload.use_llm is not None else self._settings.chat_llm_enabled
        mode = "deterministic_fallback"
        fallback_reason: str | None = None
        selection = ToolSelection(selected_tool="none", tool_input={})

        if requested_use_llm and self._settings.chat_llm_enabled and self._llm_chat_service is not None:
            try:
                selection = self._llm_chat_service.select_tool(payload)
                mode = "llm_tool_calling"
            except LLMChatError as exc:
                log_with_context(
                    logger,
                    "warning",
                    "chat.llm.failed",
                    conversation_id=conversation_id,
                    reason=exc.reason,
                    provider_status_code=exc.provider_status_code,
                )
                if not self._settings.chat_fallback_enabled:
                    return self._response(
                        conversation_id=conversation_id,
                        message="Claude is unavailable and deterministic fallback is disabled.",
                        mode="llm_tool_calling",
                        selected_tool="none",
                        tool_result={"error": {"code": exc.reason}},
                        memory_writes=memory_writes,
                        request_id=request_id,
                        trace_id=trace_id,
                        fallback_reason=exc.reason,
                    )
                selection = ToolSelection(selected_tool=route_tool(payload), tool_input={})
                fallback_reason = exc.reason
                log_with_context(logger, "info", "chat.fallback.used", reason=fallback_reason)
        else:
            selection = ToolSelection(selected_tool=route_tool(payload), tool_input={})
            if payload.use_llm is False:
                fallback_reason = None
                log_with_context(logger, "info", "chat.fallback.used", reason="request_disabled")
            else:
                fallback_reason = "llm_disabled" if requested_use_llm else None
                log_with_context(logger, "info", "chat.fallback.used", reason=fallback_reason or "request_disabled")

        log_with_context(logger, "info", "chat.tool.selected", selected_tool=selection.selected_tool)
        tool_result: dict[str, Any]
        selected_tool: ChatToolName = selection.selected_tool
        try:
            raw_tool_result = self._tool_executor.execute(
                selected_tool,
                selection.tool_input,
                payload=payload,
                conversation_id=conversation_id,
                user_id=user_id,
            )
            tool_result = compact_tool_result(selected_tool, raw_tool_result)
            if selected_tool == "write_memory" and "memory_id" in tool_result:
                memory_writes.append({"memory_id": tool_result["memory_id"], "source": "chat.write_memory"})
            message, mode, fallback_reason = self._final_message(
                payload=payload,
                selection=selection,
                tool_result=tool_result,
                mode=mode,
                fallback_reason=fallback_reason,
                conversation_id=conversation_id,
            )
        except ToolInputValidationError as exc:
            tool_result = {"error": {"code": "tool_input_validation_error", "message": str(exc)}}
            message = str(exc)
        except ToolFailureError as exc:
            tool_result = {"error": {"code": "tool_failure", "message": str(exc)}}
            message = str(exc)

        self._short_term_memory.append(
            conversation_id=conversation_id,
            event={
                "role": "assistant",
                "message": message,
                "selected_tool": selected_tool,
                "request_id": request_id,
                "trace_id": trace_id,
            },
        )
        return self._response(
            conversation_id=conversation_id,
            message=message,
            mode=mode,
            selected_tool=selected_tool,
            tool_result=tool_result,
            memory_writes=memory_writes,
            request_id=request_id,
            trace_id=trace_id,
            fallback_reason=fallback_reason,
        )

    def _final_message(
        self,
        *,
        payload: ChatRequest,
        selection: ToolSelection,
        tool_result: dict[str, Any],
        mode: str,
        fallback_reason: str | None,
        conversation_id: str,
    ) -> tuple[str, str, str | None]:
        deterministic_message = _deterministic_tool_message(selection.selected_tool, tool_result)
        if mode == "llm_tool_calling" and self._llm_chat_service is not None:
            try:
                return (
                    self._llm_chat_service.final_response(
                        payload=payload,
                        selection=selection,
                        compacted_tool_result=tool_result,
                    ),
                    mode,
                    fallback_reason,
                )
            except LLMChatError as exc:
                log_with_context(
                    logging.getLogger("app.chat"),
                    "warning",
                    "chat.llm.failed",
                    phase="final_response",
                    conversation_id=conversation_id,
                    reason=exc.reason,
                    provider_status_code=exc.provider_status_code,
                )
                if not self._settings.chat_fallback_enabled:
                    return (
                        "Claude final response is unavailable and deterministic fallback is disabled.",
                        mode,
                        exc.reason,
                    )
                return deterministic_message, "deterministic_fallback", exc.reason
        return deterministic_message, mode, fallback_reason

    def _response(
        self,
        *,
        conversation_id: str,
        message: str,
        mode: str,
        selected_tool: ChatToolName,
        tool_result: dict[str, Any],
        memory_writes: list[dict[str, Any]],
        request_id: str,
        trace_id: str,
        fallback_reason: str | None,
    ) -> ChatResponse:
        return ChatResponse(
            conversation_id=conversation_id,
            message=str(redact(message)),
            mode=mode,  # type: ignore[arg-type]
            selected_tool=selected_tool,
            tool_result=redact(tool_result),
            memory=ChatMemoryInfo(
                short_term_used=True,
                long_term_used=bool(memory_writes),
                memory_writes=memory_writes,
            ),
            request_id=request_id,
            trace_id=trace_id,
            fallback_reason=fallback_reason,
        )


def _deterministic_tool_message(tool_name: ChatToolName, tool_result: dict[str, Any]) -> str:
    if "error" in tool_result:
        return str(tool_result["error"].get("message") or "The selected tool could not run.")
    if tool_name == "classify_issue" and "label" in tool_result:
        return f"I classified this issue as {tool_result['label']}."
    if tool_name == "extract_entities":
        return "I extracted code-shaped entities from the issue text."
    if tool_name == "summarize_thread":
        return str(tool_result.get("summary") or "I summarized the issue thread.")
    if tool_name == "rag_answer":
        return str(tool_result.get("answer") or "I found relevant local corpus context.")
    if tool_name == "write_memory":
        return "I saved that memory."
    return "I handled the request."
