from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WidgetConfigResponse(BaseModel):
    public_widget_id: str
    allowed_origins: list[str] = Field(default_factory=list)
    theme: dict[str, Any] = Field(default_factory=dict)
    greeting: str
    enabled_tools: list[str] = Field(default_factory=list)

