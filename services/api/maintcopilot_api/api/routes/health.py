from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_health_service
from maintcopilot_api.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(service: HealthService = Depends(get_health_service)) -> dict[str, object]:
    return service.ready()
