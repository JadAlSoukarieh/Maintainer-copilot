from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from maintcopilot_api.repositories.base import widgets


class WidgetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_public_by_public_widget_id(self, public_widget_id: str) -> dict | None:
        row = self._session.execute(
            select(
                widgets.c.public_widget_id,
                widgets.c.allowed_origins,
                widgets.c.theme,
                widgets.c.greeting,
                widgets.c.enabled_tools,
                widgets.c.is_active,
            ).where(widgets.c.public_widget_id == public_widget_id)
        ).mappings().first()
        return dict(row) if row else None

    def get_admin_by_public_widget_id(self, public_widget_id: str) -> dict | None:
        row = self._session.execute(select(widgets).where(widgets.c.public_widget_id == public_widget_id)).mappings().first()
        return dict(row) if row else None

    def list_widgets(self) -> list[dict[str, Any]]:
        rows = self._session.execute(select(widgets).order_by(widgets.c.created_at.asc())).mappings().all()
        return [dict(row) for row in rows]

    def create_widget(
        self,
        *,
        public_widget_id: str,
        allowed_origins: list[str],
        theme: dict[str, Any],
        greeting: str,
        enabled_tools: list[str],
        created_by_user_id: str,
    ) -> dict:
        widget_id = str(uuid.uuid4())
        self._session.execute(
            insert(widgets).values(
                id=widget_id,
                public_widget_id=public_widget_id,
                allowed_origins=allowed_origins,
                theme=theme,
                greeting=greeting,
                enabled_tools=enabled_tools,
                is_active=True,
                created_by_user_id=created_by_user_id,
                updated_by_user_id=created_by_user_id,
            )
        )
        return self.get_admin_by_public_widget_id(public_widget_id) or {}

    def update_widget(self, public_widget_id: str, values: dict[str, Any]) -> dict | None:
        self._session.execute(update(widgets).where(widgets.c.public_widget_id == public_widget_id).values(**values))
        return self.get_admin_by_public_widget_id(public_widget_id)
