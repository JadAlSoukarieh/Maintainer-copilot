from __future__ import annotations

from fastapi import APIRouter

from maintcopilot_api.infra.observability import recent_events

router = APIRouter(tags=["observability"])


@router.get("/observability/recent")
def recent_observability_events(
    limit: int = 100,
    event_type: str | None = None,
    request_id: str | None = None,
) -> dict[str, object]:
    return {
        "items": recent_events.list_events(
            limit=max(1, min(limit, 200)),
            event_type=event_type,
            request_id=request_id,
        ),
        "note": "Lightweight recent events and request IDs, not a full tracing backend.",
    }
