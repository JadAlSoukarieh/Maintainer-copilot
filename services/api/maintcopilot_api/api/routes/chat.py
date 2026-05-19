from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from maintcopilot_api.api.deps import get_chat_current_user, get_chat_service
from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.chat import ChatRequest, ChatResponse
from maintcopilot_api.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


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
