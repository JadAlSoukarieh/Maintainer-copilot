from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from maintcopilot_api.api.deps import get_rag_service
from maintcopilot_api.domain.rag import RagAnswerRequest, RagAnswerResponse
from maintcopilot_api.infra.minio import MinioStorageError
from maintcopilot_api.services.rag.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])

logger = logging.getLogger("app.rag.route")


@router.post("/answer", response_model=RagAnswerResponse)
def answer_rag_question(
    request: Request,
    payload: RagAnswerRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> RagAnswerResponse:
    response = rag_service.answer_rag_question(payload)
    _store_chunk_snapshot(request, payload, response)
    return response


def _store_chunk_snapshot(request: Request, payload: RagAnswerRequest, response: RagAnswerResponse) -> None:
    minio_client = getattr(request.app.state, "minio_client", None)
    if minio_client is None:
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"chunks/snapshots/{ts}.json"
    snapshot = {
        "timestamp": ts,
        "question": payload.question,
        "retriever": response.retriever,
        "rewritten_query": response.rewritten_query,
        "citations": [c.model_dump() for c in response.citations],
    }
    try:
        minio_client.put_json(key, snapshot)
    except MinioStorageError as exc:
        logger.warning("minio.chunk_snapshot_failed", extra={"event_fields": {"error": str(exc)}})
