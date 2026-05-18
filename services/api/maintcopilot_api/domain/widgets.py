from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_TOOLS = {
    "classify_issue",
    "extract_entities",
    "summarize_thread",
    "rag_answer",
    "write_memory",
}
ALLOWED_POSITIONS = {"bottom-right", "bottom-left", "inline"}
HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _validate_origin(value: str) -> str:
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Origin must include http or https and a host.")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Origin must not include a path, query string, or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}"


class WidgetTheme(BaseModel):
    primaryColor: str = "#1f6feb"
    position: str = "bottom-right"

    @field_validator("primaryColor")
    @classmethod
    def validate_primary_color(cls, value: str) -> str:
        if not HEX_COLOR_PATTERN.match(value):
            raise ValueError("primaryColor must be a hex color.")
        return value

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: str) -> str:
        if value not in ALLOWED_POSITIONS:
            raise ValueError("position is not supported.")
        return value


class WidgetConfigResponse(BaseModel):
    public_widget_id: str
    allowed_origins: list[str] = Field(default_factory=list)
    theme: WidgetTheme = Field(default_factory=WidgetTheme)
    greeting: str
    enabled_tools: list[str] = Field(default_factory=list)

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: list[str]) -> list[str]:
        return [_validate_origin(item) for item in value]

    @field_validator("enabled_tools")
    @classmethod
    def validate_enabled_tools(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - ALLOWED_TOOLS)
        if invalid:
            raise ValueError(f"Unsupported tools requested: {', '.join(invalid)}")
        return value


class WidgetCreateRequest(BaseModel):
    public_widget_id: str = Field(min_length=3, max_length=100)
    allowed_origins: list[str]
    theme: WidgetTheme = Field(default_factory=WidgetTheme)
    greeting: str = Field(min_length=1, max_length=1000)
    enabled_tools: list[str] = Field(default_factory=list)

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one allowed origin is required.")
        return [_validate_origin(item) for item in value]

    @field_validator("enabled_tools")
    @classmethod
    def validate_enabled_tools(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - ALLOWED_TOOLS)
        if invalid:
            raise ValueError(f"Unsupported tools requested: {', '.join(invalid)}")
        return value


class WidgetUpdateRequest(BaseModel):
    allowed_origins: list[str] | None = None
    theme: WidgetTheme | None = None
    greeting: str | None = Field(default=None, min_length=1, max_length=1000)
    enabled_tools: list[str] | None = None
    is_active: bool | None = None

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("At least one allowed origin is required.")
        return [_validate_origin(item) for item in value]

    @field_validator("enabled_tools")
    @classmethod
    def validate_enabled_tools(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        invalid = sorted(set(value) - ALLOWED_TOOLS)
        if invalid:
            raise ValueError(f"Unsupported tools requested: {', '.join(invalid)}")
        return value

    @model_validator(mode="after")
    def validate_not_empty(self) -> "WidgetUpdateRequest":
        if all(getattr(self, field) is None for field in {"allowed_origins", "theme", "greeting", "enabled_tools", "is_active"}):
            raise ValueError("At least one widget field must be updated.")
        return self


class WidgetAdminResponse(BaseModel):
    id: str
    public_widget_id: str
    allowed_origins: list[str]
    theme: WidgetTheme
    greeting: str
    enabled_tools: list[str]
    is_active: bool
    created_by_user_id: str | None = None
    updated_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class WidgetAdminListResponse(BaseModel):
    items: list[WidgetAdminResponse] = Field(default_factory=list)


class WidgetDisableResponse(BaseModel):
    public_widget_id: str
    status: str
