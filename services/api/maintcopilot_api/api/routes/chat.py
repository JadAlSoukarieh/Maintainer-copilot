from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from maintcopilot_api.api.deps import get_chat_current_user, get_chat_service, get_settings, get_short_term_memory_store
from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.chat import ChatRequest, ChatResponse
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.services.chat_service import ChatService
from maintcopilot_api.services.short_term_memory import ShortTermMemoryStore

router = APIRouter(tags=["chat"])

_TOOL_STATUS: dict[str, str] = {
    "classify_issue": "Classifying issue…",
    "extract_entities": "Extracting entities…",
    "summarize_thread": "Summarizing thread…",
    "rag_answer": "Searching Node.js docs…",
    "write_memory": "Saving to memory…",
    "none": "Processing…",
}


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    service: ChatService = Depends(get_chat_service),
    current_user: UserRead | None = Depends(get_chat_current_user),
) -> ChatResponse:
    return service.chat(
        payload,
        request_id=getattr(request.state, "request_id", "unknown"),
        trace_id=getattr(request.state, "trace_id", "unknown"),
        current_user=current_user,
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(
    payload: ChatRequest,
    request: Request,
    service: ChatService = Depends(get_chat_service),
    current_user: UserRead | None = Depends(get_chat_current_user),
) -> StreamingResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    trace_id = getattr(request.state, "trace_id", "unknown")

    async def generate() -> AsyncIterator[str]:
        yield _sse("status", {"type": "thinking", "text": "Analyzing your message…"})

        try:
            result: ChatResponse = await asyncio.to_thread(
                service.chat,
                payload,
                request_id=request_id,
                trace_id=trace_id,
                current_user=current_user,
            )
        except Exception:
            yield _sse("error", {"message": "Something went wrong. Please try again."})
            return

        tool = result.selected_tool
        yield _sse("status", {"type": "tool", "tool": tool, "text": _TOOL_STATUS.get(tool, "Processing…")})

        words = result.message.split(" ")
        for i, word in enumerate(words):
            token = word + ("" if i == len(words) - 1 else " ")
            yield _sse("token", {"text": token})
            await asyncio.sleep(0.018)

        yield _sse("done", result.model_dump(mode="json"))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/{conversation_id}/memory")
def chat_memory(
    conversation_id: str,
    request: Request,
    limit: int = 100,
    current_user: UserRead | None = Depends(get_chat_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    store: ShortTermMemoryStore = get_short_term_memory_store(request, settings)
    return {
        "conversation_id": conversation_id,
        "items": store.list_events(conversation_id=conversation_id, limit=max(1, min(limit, 200))),
        "storage": "redis" if not settings.allow_in_memory_memory else "in_memory_dev",
    }
