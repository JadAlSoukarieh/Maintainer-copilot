from __future__ import annotations

from maintcopilot_api.services.rag.corpus import build_doc_corpus_rows, build_issue_corpus_rows, validate_corpus_row
from maintcopilot_api.services.rag.retrieval import SparseRetriever


def test_tfidf_retrieval_returns_relevant_chunk() -> None:
    rows = [
        {
            "chunk_id": "doc-http-001",
            "source_type": "doc",
            "source_id": "http.md",
            "title": "http docs",
            "url": "",
            "text": "Document: http docs\nSection: Debugging\nUse NODE_DEBUG=http and inspect request lifecycle for connection leaks.",
            "metadata": {
                "repo": "nodejs/node",
                "source_split": "docs",
                "label": None,
                "issue_number": None,
                "created_at": None,
                "closed_at": None,
                "path": "http.md",
                "section": "Debugging",
            },
        },
        {
            "chunk_id": "issue-1-test-001",
            "source_type": "resolved_issue",
            "source_id": "1",
            "title": "child_process question",
            "url": "https://github.com/nodejs/node/issues/1",
            "text": "Issue: child_process question\n\nProblem:\nHow do I spawn a process on Windows?",
            "metadata": {
                "repo": "nodejs/node",
                "source_split": "test",
                "label": "question",
                "issue_number": 1,
                "created_at": "2016-01-01T00:00:00Z",
                "closed_at": "2016-01-02T00:00:00Z",
                "path": None,
                "section": "issue_record",
            },
        },
    ]
    retriever = SparseRetriever(rows)
    results = retriever.query("Where do the docs explain http request debugging?", top_k=2)
    assert results
    assert results[0]["chunk_id"] == "doc-http-001"


def test_corpus_rows_validate_required_fields() -> None:
    row = {
        "chunk_id": "issue-9001-test-001",
        "source_type": "resolved_issue",
        "source_id": "9001",
        "title": "https.request leak",
        "url": "https://github.com/nodejs/node/issues/9001",
        "text": "Issue: https.request leak",
        "metadata": {
            "repo": "nodejs/node",
            "source_split": "test",
            "label": "bug",
            "issue_number": 9001,
            "created_at": "2016-09-01T00:00:00Z",
            "closed_at": "2016-09-02T00:00:00Z",
            "path": None,
            "section": "issue_record",
        },
    }
    validate_corpus_row(row)


def test_docs_and_issues_can_coexist_in_same_corpus(tmp_path) -> None:
    docs_dir = tmp_path / "node_docs"
    docs_dir.mkdir()
    (docs_dir / "api.md").write_text("# API\n\n## Debugging\nUse NODE_DEBUG=http.\n", encoding="utf-8")

    issue_record = {
        "repo": "nodejs/node",
        "issue_number": 9001,
        "url": "https://github.com/nodejs/node/issues/9001",
        "title": "https.request leaks memory",
        "body": "Repro: send many requests. Actual: heap keeps growing.",
        "created_at": "2016-09-01T00:00:00Z",
        "closed_at": "2016-09-02T00:00:00Z",
        "label": "bug",
    }

    doc_rows = build_doc_corpus_rows(docs_dir, max_chars=300)
    issue_rows = build_issue_corpus_rows([issue_record], source_split="test", max_chars=300)
    rows = doc_rows + issue_rows

    assert any(row["source_type"] == "doc" for row in rows)
    assert any(row["source_type"] == "resolved_issue" for row in rows)

    retriever = SparseRetriever(rows)
    results = retriever.query("How do the docs recommend http debugging?", top_k=3)
    assert results
    assert results[0]["source_type"] == "doc"
