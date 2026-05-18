from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from maintcopilot_api.repositories.base import widgets


class WidgetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_public_widget_id(self, public_widget_id: str) -> dict | None:
        result = self._session.execute(
            select(
                widgets.c.public_widget_id,
                widgets.c.allowed_origins,
                widgets.c.theme,
                widgets.c.greeting,
                widgets.c.enabled_tools,
            ).where(widgets.c.public_widget_id == public_widget_id)
        ).first()
        if result is None:
            return None
        return {
            "public_widget_id": result.public_widget_id,
            "allowed_origins": result.allowed_origins,
            "theme": result.theme,
            "greeting": result.greeting,
            "enabled_tools": result.enabled_tools,
        }
