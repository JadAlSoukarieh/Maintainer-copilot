from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_chat_service
from maintcopilot_api.domain.chat import ChatRequest, ChatResponse
from maintcopilot_api.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, service: ChatService = Depends(get_chat_service)) -> ChatResponse:
    return service.chat(payload)
