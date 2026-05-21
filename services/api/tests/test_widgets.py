from __future__ import annotations

import json
from types import SimpleNamespace

from pydantic import ValidationError
import pytest

from maintcopilot_api.api.deps import require_admin
from maintcopilot_api.api.error_handlers import domain_error_handler
from maintcopilot_api.api.routes.widgets import create_widget, disable_widget, widget_config, widget_loader
from maintcopilot_api.domain.auth import UserRead, UserRole
from maintcopilot_api.domain.errors import ForbiddenError, NotFoundError
from maintcopilot_api.domain.widgets import WidgetCreateRequest
from maintcopilot_api.infra.config import Settings


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
    request = SimpleNamespace(headers={"origin": "http://localhost:8090"})
    response = widget_config("widget_123", widget_service, Settings(require_vault=False, chat_llm_enabled=False), request)
    assert response.public_widget_id == "widget_123"
    assert response.greeting == "Hello maintainer"
    assert response.theme.primaryColor == "#1f6feb"
    assert response.enabled_tools == ["classify_issue", "summarize_thread"]
    assert response.default_use_llm is False


def test_widget_loader_returns_iframe_injection_javascript() -> None:
    widget_service = _demo_widget_service()
    request = SimpleNamespace(headers={"origin": "http://localhost:5173"})
    response = widget_loader("demo-widget", widget_service, Settings(require_vault=False, enable_demo_widget_fallback=True), request)
    body = response.body.decode("utf-8")

    assert response.media_type == "application/javascript"
    assert "data-widget-id" in body
    assert "Maintainer's Copilot Widget" in body
    assert "document.createElement(\"iframe\")" in body
    assert "maintcopilot:resize" in body
    assert (
        "frame-ancestors http://localhost:8000 http://localhost:5173 http://localhost:8080 http://localhost:8090"
        == response.headers["Content-Security-Policy"]
    )


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


def test_demo_widget_fallback_disabled_by_default(widget_service) -> None:
    with pytest.raises(NotFoundError):
        widget_service.get_public_config("demo-widget")


def test_demo_widget_fallback_enabled_returns_config(widget_service) -> None:
    response = widget_service.get_public_config("demo-widget", enable_demo_fallback=True)

    assert response.public_widget_id == "demo-widget"
    assert response.theme.primaryColor == "#1f6feb"
    assert response.theme.position == "bottom-right"
    assert response.greeting == "Ask Maintainer's Copilot about this project."
    assert response.enabled_tools == ["classify_issue", "extract_entities", "summarize_thread", "rag_answer", "write_memory"]
    assert "http://localhost:5173" in response.allowed_origins
    assert response.default_use_llm is False


def test_demo_widget_fallback_does_not_apply_to_random_widget(widget_service) -> None:
    with pytest.raises(NotFoundError):
        widget_service.get_public_config("not-demo-widget", enable_demo_fallback=True)


def test_widget_config_route_uses_demo_fallback_flag(widget_service) -> None:
    request = SimpleNamespace(headers={"origin": "http://localhost:5173"})
    response = widget_config(
        "demo-widget",
        widget_service,
        Settings(require_vault=False, enable_demo_widget_fallback=True, chat_llm_enabled=True),
        request,
    )

    assert response.public_widget_id == "demo-widget"
    assert response.default_use_llm is True


def test_disallowed_widget_origin_fails(widget_service) -> None:
    request = SimpleNamespace(headers={"origin": "http://evil.example"})

    with pytest.raises(ForbiddenError):
        widget_config("demo-widget", widget_service, Settings(require_vault=False, enable_demo_widget_fallback=True), request)


def test_missing_origin_allowed_only_in_demo_mode(widget_service) -> None:
    with pytest.raises(ForbiddenError):
        widget_config(
            "demo-widget",
            _demo_widget_service(),
            Settings(require_vault=False, enable_demo_widget_fallback=False),
            SimpleNamespace(headers={}),
        )

    response = widget_config("demo-widget", widget_service, Settings(require_vault=False, enable_demo_widget_fallback=True), SimpleNamespace(headers={}))
    assert response.public_widget_id == "demo-widget"


def _demo_widget_service():
    class _Service:
        def get_public_config(self, public_widget_id: str, *, enable_demo_fallback: bool = False):
            from maintcopilot_api.services.widget_service import demo_widget_config

            assert public_widget_id == "demo-widget"
            return demo_widget_config()

    return _Service()
