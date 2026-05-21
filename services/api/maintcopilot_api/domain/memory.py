from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryWriteRequest(BaseModel):
    user_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryWriteResponse(BaseModel):
    memory_id: str
    status: str


class MemorySearchRequest(BaseModel):
    query: str = ""
    top_k: int = Field(default=10, ge=1, le=200)
    mode: str = Field(default="hybrid", pattern="^(vector|text|hybrid)$")
