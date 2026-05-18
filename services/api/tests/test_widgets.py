from __future__ import annotations

import json
from types import SimpleNamespace

from pydantic import ValidationError
import pytest

from maintcopilot_api.api.deps import require_admin
from maintcopilot_api.api.error_handlers import domain_error_handler
from maintcopilot_api.api.routes.widgets import create_widget, disable_widget, widget_config
from maintcopilot_api.domain.auth import UserRead, UserRole
from maintcopilot_api.domain.errors import ForbiddenError, NotFoundError
from maintcopilot_api.domain.widgets import WidgetCreateRequest


def test_public_widget_config_can_be_fetched(widget_service, seed_user) -> None:
    admin_user = UserRead(**seed_user(email="admin@example.com", role=UserRole.ADMIN))
    payload = WidgetCreateRequest(
        public_widget_id="widget_123",
        allowed_origins=["http://localhost:8090"],
        theme={"primaryColor": "#1f6feb", "position": "bottom-right"},
        greeting="Hello maintainer",
        enabled_tools=["classify_issue", "summarize_thread"],
    )
    create_widget(payload, admin_user, widget_service)
    response = widget_config("widget_123", widget_service)
    assert response.public_widget_id == "widget_123"
    assert response.enabled_tools == ["classify_issue", "summarize_thread"]


@pytest.mark.anyio
async def test_unknown_widget_returns_structured_404(widget_service) -> None:
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-widget-404"))
    with pytest.raises(NotFoundError) as exc_info:
        widget_service.get_public_config("missing-widget")
    response = await domain_error_handler(request, exc_info.value)
    assert response.status_code == 404
    assert json.loads(response.body) == {
        "error": {
            "code": "not_found",
            "message": "Widget config was not found.",
            "request_id": "req-widget-404",
        }
    }


def test_normal_user_cannot_create_widget_config(seed_user) -> None:
    normal_user = UserRead(**seed_user(email="user@example.com", role=UserRole.USER))
    with pytest.raises(ForbiddenError):
        require_admin(normal_user)


def test_admin_can_create_widget_config(widget_service, seed_user, audit_repository) -> None:
    admin_user = UserRead(**seed_user(email="admin@example.com", role=UserRole.ADMIN))
    payload = WidgetCreateRequest(
        public_widget_id="widget_admin_create",
        allowed_origins=["http://localhost:8090"],
        theme={"primaryColor": "#0f172a", "position": "bottom-left"},
        greeting="Configured widget",
        enabled_tools=["extract_entities"],
    )
    response = create_widget(payload, admin_user, widget_service)
    event_types = [event["event_type"] for event in audit_repository.list_events()]
    assert response.public_widget_id == "widget_admin_create"
    assert response.created_by_user_id == admin_user.id
    assert "widget_created" in event_types


def test_invalid_origin_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WidgetCreateRequest(
            public_widget_id="widget_invalid_origin",
            allowed_origins=["localhost:8090/path"],
            theme={"primaryColor": "#1f6feb", "position": "bottom-right"},
            greeting="Hello",
            enabled_tools=["classify_issue"],
        )


def test_invalid_enabled_tool_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WidgetCreateRequest(
            public_widget_id="widget_invalid_tool",
            allowed_origins=["http://localhost:8090"],
            theme={"primaryColor": "#1f6feb", "position": "bottom-right"},
            greeting="Hello",
            enabled_tools=["unknown_tool"],
        )


def test_disabling_widget_makes_public_config_unavailable(widget_service, seed_user) -> None:
    admin_user = UserRead(**seed_user(email="admin@example.com", role=UserRole.ADMIN))
    payload = WidgetCreateRequest(
        public_widget_id="widget_disable",
        allowed_origins=["http://localhost:8090"],
        theme={"primaryColor": "#1f6feb", "position": "bottom-right"},
        greeting="Hello",
        enabled_tools=["write_memory"],
    )
    create_widget(payload, admin_user, widget_service)
    disable_widget("widget_disable", admin_user, widget_service)
    with pytest.raises(NotFoundError):
        widget_service.get_public_config("widget_disable")
