from __future__ import annotations

from maintcopilot_api.domain.widgets import WidgetConfigResponse
from maintcopilot_api.repositories.widget_repository import WidgetRepository


class WidgetService:
    def __init__(self, repository: WidgetRepository) -> None:
        self._repository = repository

    def get_config(self, widget_id: str) -> WidgetConfigResponse:
        record = self._repository.get_by_public_widget_id(widget_id)
        if record is None:
            return WidgetConfigResponse(
                public_widget_id=widget_id,
                allowed_origins=["http://localhost:3000", "http://localhost:8080"],
                theme={"mode": "light", "accent": "#1f6feb"},
                greeting="Maintainer's Copilot widget placeholder",
                enabled_tools=["classify", "ner", "summarize"],
            )
        return WidgetConfigResponse(**record)
