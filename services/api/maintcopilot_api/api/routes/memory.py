from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_memory_service
from maintcopilot_api.domain.memory import MemoryWriteRequest, MemoryWriteResponse
from maintcopilot_api.services.memory_service import MemoryService

router = APIRouter(tags=["memory"])


@router.post("/memory", response_model=MemoryWriteResponse)
def create_memory(
    payload: MemoryWriteRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryWriteResponse:
    return service.create(payload)
