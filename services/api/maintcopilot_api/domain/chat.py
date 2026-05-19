from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChatToolName = Literal[
    "classify_issue",
    "extract_entities",
    "summarize_thread",
    "rag_answer",
    "write_memory",
    "none",
]
ChatMode = Literal["llm_tool_calling", "deterministic_fallback"]


class ChatContext(BaseModel):
    issue_title: str | None = None
    issue_body: str | None = None
    issue_url: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1)
    context: ChatContext = Field(default_factory=ChatContext)
    use_llm: bool = True


class ChatMemoryInfo(BaseModel):
    short_term_used: bool
    long_term_used: bool
    memory_writes: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    mode: ChatMode
    selected_tool: ChatToolName
    tool_result: dict[str, Any] = Field(default_factory=dict)
    memory: ChatMemoryInfo
    request_id: str
    trace_id: str
    fallback_reason: str | None = None
