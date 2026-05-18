from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_widget_service
from maintcopilot_api.domain.widgets import WidgetConfigResponse
from maintcopilot_api.services.widget_service import WidgetService

router = APIRouter(tags=["widgets"])


@router.get("/widgets/{widget_id}/config", response_model=WidgetConfigResponse)
def widget_config(widget_id: str, service: WidgetService = Depends(get_widget_service)) -> WidgetConfigResponse:
    return service.get_config(widget_id)
