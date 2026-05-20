from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from maintcopilot_api.api.deps import get_settings, get_widget_service, require_admin
from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.infra.config import Settings
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


WIDGET_LOADER_JS = r"""
(function () {
  var script = document.currentScript;
  if (!script) return;
  var widgetId = script.getAttribute("data-widget-id") || "demo-widget";
  var apiBaseUrl = script.getAttribute("data-api-base-url") || window.location.origin;
  var widgetUrl = script.getAttribute("data-widget-url") || apiBaseUrl;
  var iframeId = "maintcopilot-widget-frame-" + widgetId;
  if (document.getElementById(iframeId)) return;

  var iframe = document.createElement("iframe");
  iframe.id = iframeId;
  iframe.title = "Maintainer's Copilot Widget";
  iframe.src = widgetUrl.replace(/\/$/, "") + "?widget_id=" + encodeURIComponent(widgetId) + "&api_base_url=" + encodeURIComponent(apiBaseUrl);
  iframe.style.position = "fixed";
  iframe.style.right = "16px";
  iframe.style.bottom = "16px";
  iframe.style.width = "380px";
  iframe.style.height = "92px";
  iframe.style.border = "0";
  iframe.style.zIndex = "2147483000";
  iframe.style.colorScheme = "normal";
  iframe.setAttribute("allow", "clipboard-write");
  document.body.appendChild(iframe);

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "maintcopilot:resize") return;
    if (event.source !== iframe.contentWindow) return;
    var height = Math.max(80, Math.min(Number(event.data.height) || 92, 720));
    iframe.style.height = height + "px";
    iframe.style.width = event.data.expanded ? "380px" : "92px";
  });
})();
"""


@router.get("/widgets/{public_widget_id}/config", response_model=WidgetConfigResponse)
def widget_config(
    public_widget_id: str,
    service: WidgetService = Depends(get_widget_service),
    settings: Settings = Depends(get_settings),
) -> WidgetConfigResponse:
    enable_fallback = bool(getattr(settings, "enable_demo_widget_fallback", False))
    return service.get_public_config(public_widget_id, enable_demo_fallback=enable_fallback)


@router.get("/widget.js", include_in_schema=False)
def widget_loader() -> Response:
    return Response(content=WIDGET_LOADER_JS, media_type="application/javascript")


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
