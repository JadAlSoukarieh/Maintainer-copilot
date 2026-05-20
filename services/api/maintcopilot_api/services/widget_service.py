from __future__ import annotations

from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.errors import ConflictError, NotFoundError
from maintcopilot_api.domain.widgets import (
    WidgetAdminListResponse,
    WidgetAdminResponse,
    WidgetConfigResponse,
    WidgetCreateRequest,
    WidgetDisableResponse,
    WidgetUpdateRequest,
)
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.repositories.widget_repository import WidgetRepository


class WidgetService:
    def __init__(self, repository: WidgetRepository, audit_repository: AuditRepository, session) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._session = session

    def get_public_config(self, public_widget_id: str, *, enable_demo_fallback: bool = False) -> WidgetConfigResponse:
        record = self._repository.get_public_by_public_widget_id(public_widget_id)
        if record is None or not record["is_active"]:
            if enable_demo_fallback and public_widget_id == "demo-widget":
                return demo_widget_config()
            raise NotFoundError("Widget config was not found.")
        return WidgetConfigResponse(**record)

    def list_widgets(self, current_user: UserRead) -> WidgetAdminListResponse:
        records = self._repository.list_widgets()
        return WidgetAdminListResponse(items=[WidgetAdminResponse(**record) for record in records])

    def create_widget(self, payload: WidgetCreateRequest, current_user: UserRead) -> WidgetAdminResponse:
        existing = self._repository.get_admin_by_public_widget_id(payload.public_widget_id)
        if existing is not None:
            raise ConflictError("A widget with this public_widget_id already exists.")
        record = self._repository.create_widget(
            public_widget_id=payload.public_widget_id,
            allowed_origins=payload.allowed_origins,
            theme=payload.theme.model_dump(),
            greeting=payload.greeting,
            enabled_tools=payload.enabled_tools,
            created_by_user_id=current_user.id,
        )
        self._audit_repository.create_event(
            event_type="widget_created",
            actor_id=current_user.id,
            payload={"public_widget_id": payload.public_widget_id},
        )
        self._session.commit()
        return WidgetAdminResponse(**record)

    def update_widget(
        self,
        public_widget_id: str,
        payload: WidgetUpdateRequest,
        current_user: UserRead,
    ) -> WidgetAdminResponse:
        existing = self._repository.get_admin_by_public_widget_id(public_widget_id)
        if existing is None:
            raise NotFoundError("Widget config was not found.")
        values = payload.model_dump(exclude_none=True)
        if "theme" in values:
            values["theme"] = payload.theme.model_dump() if payload.theme else existing["theme"]
        values["updated_by_user_id"] = current_user.id
        record = self._repository.update_widget(public_widget_id, values)
        self._audit_repository.create_event(
            event_type="widget_updated",
            actor_id=current_user.id,
            payload={"public_widget_id": public_widget_id, "updated_fields": sorted(values.keys())},
        )
        self._session.commit()
        return WidgetAdminResponse(**(record or existing))

    def disable_widget(self, public_widget_id: str, current_user: UserRead) -> WidgetDisableResponse:
        existing = self._repository.get_admin_by_public_widget_id(public_widget_id)
        if existing is None:
            raise NotFoundError("Widget config was not found.")
        self._repository.update_widget(
            public_widget_id,
            {"is_active": False, "updated_by_user_id": current_user.id},
        )
        self._audit_repository.create_event(
            event_type="widget_disabled",
            actor_id=current_user.id,
            payload={"public_widget_id": public_widget_id},
        )
        self._session.commit()
        return WidgetDisableResponse(public_widget_id=public_widget_id, status="disabled")


def demo_widget_config() -> WidgetConfigResponse:
    return WidgetConfigResponse(
        public_widget_id="demo-widget",
        theme={"primaryColor": "#1f6feb", "position": "bottom-right"},
        greeting="Ask Maintainer's Copilot about this project.",
        enabled_tools=["classify_issue", "extract_entities", "summarize_thread", "rag_answer", "write_memory"],
        allowed_origins=["http://localhost:8000", "http://localhost:5173", "http://localhost:8090"],
    )
