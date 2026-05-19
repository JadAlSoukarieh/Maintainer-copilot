from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_rag_service
from maintcopilot_api.domain.rag import RagAnswerRequest, RagAnswerResponse
from maintcopilot_api.services.rag.rag_service import RagService


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/answer", response_model=RagAnswerResponse)
def answer_rag_question(
    payload: RagAnswerRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> RagAnswerResponse:
    # TODO: require authenticated users when chatbot tool auth is wired end-to-end.
    return rag_service.answer_rag_question(payload)
