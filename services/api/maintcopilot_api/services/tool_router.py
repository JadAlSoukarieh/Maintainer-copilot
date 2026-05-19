from __future__ import annotations

from maintcopilot_api.domain.chat import ChatRequest, ChatToolName


MEMORY_INTENT_TERMS = ("remember", "save", "note that", "note this", "keep in mind")


def route_tool(payload: ChatRequest) -> ChatToolName:
    text = payload.message.lower()
    if any(term in text for term in ("classify", "label", "triage")):
        return "classify_issue"
    if any(term in text for term in ("entities", "entity", "files", "functions", "error codes", "versions")):
        return "extract_entities"
    if any(term in text for term in ("summarize", "summary", "tldr", "tl;dr", "recap")):
        return "summarize_thread"
    if has_explicit_memory_intent(payload.message):
        return "write_memory"
    if any(term in text for term in ("docs", "documentation", "how", "where", "explain", "similar issue", "resolved issue")):
        return "rag_answer"
    return "rag_answer"


def has_explicit_memory_intent(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in MEMORY_INTENT_TERMS)
