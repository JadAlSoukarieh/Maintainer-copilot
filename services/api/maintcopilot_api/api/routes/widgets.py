from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_widget_service, require_admin
from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.widgets import (
    WidgetAdminListResponse,
    WidgetAdminResponse,
    WidgetConfigResponse,
    WidgetCreateRequest,
    WidgetDisableResponse,
    WidgetUpdateRequest,
)
from maintcopilot_api.services.widget_service import WidgetService

router = APIRouter(tags=["widgets"])


@router.get("/widgets/{public_widget_id}/config", response_model=WidgetConfigResponse)
def widget_config(public_widget_id: str, service: WidgetService = Depends(get_widget_service)) -> WidgetConfigResponse:
    return service.get_public_config(public_widget_id)


@router.get("/admin/widgets", response_model=WidgetAdminListResponse)
def list_widgets(
    current_user: UserRead = Depends(require_admin),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetAdminListResponse:
    return service.list_widgets(current_user)


@router.post("/admin/widgets", response_model=WidgetAdminResponse)
def create_widget(
    payload: WidgetCreateRequest,
    current_user: UserRead = Depends(require_admin),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetAdminResponse:
    return service.create_widget(payload, current_user)


@router.patch("/admin/widgets/{public_widget_id}", response_model=WidgetAdminResponse)
def update_widget(
    public_widget_id: str,
    payload: WidgetUpdateRequest,
    current_user: UserRead = Depends(require_admin),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetAdminResponse:
    return service.update_widget(public_widget_id, payload, current_user)


@router.delete("/admin/widgets/{public_widget_id}", response_model=WidgetDisableResponse)
def disable_widget(
    public_widget_id: str,
    current_user: UserRead = Depends(require_admin),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetDisableResponse:
    return service.disable_widget(public_widget_id, current_user)
