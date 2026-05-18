from __future__ import annotations

from maintcopilot_api.domain.chat import ChatRequest, ChatResponse
from maintcopilot_api.infra.model_client import ModelServerClient


class ChatService:
    def __init__(self, model_client: ModelServerClient) -> None:
        self._model_client = model_client

    def chat(self, payload: ChatRequest) -> ChatResponse:
        classification = self._model_client.preview_classification(payload.message)
        return ChatResponse(
            answer="Chat orchestration placeholder. RAG, auth, and memory-aware responses are not implemented yet.",
            classification=classification,
            sources=[],
            trace_note="placeholder_response",
        )
