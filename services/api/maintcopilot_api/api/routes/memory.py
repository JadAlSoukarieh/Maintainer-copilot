from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_chat_current_user, get_memory_service
from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.memory import MemorySearchRequest, MemoryWriteRequest, MemoryWriteResponse
from maintcopilot_api.services.memory_service import MemoryService

router = APIRouter(tags=["memory"])


@router.post("/memory", response_model=MemoryWriteResponse)
def create_memory(
    payload: MemoryWriteRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryWriteResponse:
    return service.create(payload)


@router.get("/memory")
def list_memories(
    limit: int = 50,
    current_user: UserRead | None = Depends(get_chat_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> dict[str, object]:
    user_id = None if current_user is None or current_user.role == "admin" else current_user.id
    return {
        "items": service.list_memories(user_id=user_id, limit=max(1, min(limit, 200))),
        "storage": "text_metadata_pgvector",
        "vector_status": service.vector_status(),
    }


@router.post("/memory/search")
def search_memories(
    payload: MemorySearchRequest,
    current_user: UserRead | None = Depends(get_chat_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> dict[str, object]:
    user_id = None if current_user is None or current_user.role == "admin" else current_user.id
    result = service.search_memories(
        query_text=payload.query,
        user_id=user_id,
        limit=payload.top_k,
        mode=payload.mode,
    )
    result["storage"] = "text_metadata_pgvector"
    result["vector_status"] = service.vector_status()
    return result
