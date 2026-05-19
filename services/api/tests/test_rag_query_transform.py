from __future__ import annotations

from maintcopilot_api.services.rag.query_transform import rewrite_query


def test_rewrite_detects_docs_api_intent() -> None:
    result = rewrite_query("Where does the API documentation explain fs readFile parameters?")

    assert result.preferred_source_type == "doc"
    assert result.intent == "api"
    assert "stream" in result.added_terms
    assert "buffer" in result.added_terms


def test_rewrite_detects_debug_memory_issue_intent() -> None:
    result = rewrite_query("How do I debug a memory leak in https request?")

    assert result.preferred_source_type == "resolved_issue"
    assert result.intent == "memory"
    assert "heap" in result.added_terms
    assert "clientrequest" in result.added_terms


def test_rewrite_expands_node_specific_terms_without_duplicates() -> None:
    result = rewrite_query("ECONNRESET in https request")

    assert result.added_terms.count("ECONNRESET") == 0
    assert "socket" in result.added_terms
    assert "connection reset" in result.added_terms
    assert "http" in result.added_terms
