from __future__ import annotations

from maintcopilot_api.domain.rag import QueryRewriteResult


EXPANSIONS: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (("https request", "https.request", "http request", "http.request"), ["http", "https", "request", "clientrequest"]),
    (("memory leak",), ["memory", "leak", "heap", "allocation", "gc"]),
    (("dns error",), ["dns", "NODATA", "TIMEOUT", "resolver"]),
    (("stream pipeline", "stream.pipeline"), ["stream", "pipeline", "destroy", "cleanup"]),
    (("fs readfile", "fs.readfile", "readfile"), ["fs", "readFile", "stream", "buffer", "memory"]),
    (("tls",), ["tls", "secureOptions", "certificate", "handshake"]),
    (("crypto",), ["crypto", "FIPS", "hash", "cipher"]),
    (("econnreset",), ["ECONNRESET", "socket", "http", "https", "connection reset"]),
)

DOC_TERMS = {"doc", "docs", "documentation", "reference", "api", "method", "parameter", "explain"}
ISSUE_TERMS = {"issue", "bug", "crash", "error", "regression", "failing", "segfault", "econnreset"}
MEMORY_TERMS = {"memory", "leak", "heap", "allocation", "gc"}
NETWORK_TERMS = {"http", "https", "tls", "socket", "connection", "network", "econnreset"}
MODULE_INTENTS = {
    "crypto": "crypto",
    "stream": "stream",
    "pipeline": "stream",
    "fs": "fs",
    "readfile": "fs",
    "dns": "dns",
}


def rewrite_query(query: str) -> QueryRewriteResult:
    original = query.strip()
    lowered = original.lower()
    normalized = lowered.replace("_", " ").replace("-", " ")
    tokens = set(normalized.replace(".", " ").split())
    added_terms: list[str] = []

    for triggers, terms in EXPANSIONS:
        if any(trigger in normalized for trigger in triggers):
            for term in terms:
                _append_unique(added_terms, term, original)

    intent = "unknown"
    preferred_source_type = None
    if tokens & DOC_TERMS:
        preferred_source_type = "doc"
        intent = "api" if "api" in tokens or "method" in tokens or "parameter" in tokens else "docs"
    if tokens & ISSUE_TERMS:
        preferred_source_type = "resolved_issue"
        intent = "debug"
    if tokens & MEMORY_TERMS or "memory leak" in normalized:
        preferred_source_type = "resolved_issue"
        intent = "memory"
    elif tokens & NETWORK_TERMS and intent in {"debug", "unknown"}:
        intent = "network"
    for term, module_intent in MODULE_INTENTS.items():
        if term in normalized and intent == "unknown":
            intent = module_intent

    rewritten_query = original
    if added_terms:
        rewritten_query = f"{original} {' '.join(added_terms)}"

    return QueryRewriteResult(
        original_query=original,
        rewritten_query=rewritten_query,
        added_terms=added_terms,
        intent=intent,
        preferred_source_type=preferred_source_type,
    )


def _append_unique(items: list[str], value: str, original: str) -> None:
    folded = {item.lower() for item in items}
    original_terms = set(original.lower().replace(".", " ").split())
    if value.lower() not in folded and value.lower() not in original_terms:
        items.append(value)
