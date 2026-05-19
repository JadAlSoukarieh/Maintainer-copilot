from __future__ import annotations

from maintcopilot_api.services.rag.chunking import chunk_issue_record, chunk_markdown_document, split_long_text
from maintcopilot_api.services.rag.corpus import (
    build_doc_corpus_rows,
    build_issue_corpus_rows,
    collapse_redundant_leading_segment,
    discover_doc_paths,
    validate_corpus_row,
)


def test_markdown_heading_chunking_preserves_section_title() -> None:
    chunks = chunk_markdown_document(
        title="http docs",
        text="# Overview\nGeneral intro.\n\n## Debugging\nUse NODE_DEBUG=http to inspect requests.",
        path="http.md",
        max_chars=160,
    )
    sections = {chunk["metadata"]["section"] for chunk in chunks}
    assert "Overview" in sections
    assert "Overview > Debugging" in sections
    assert any("Section path: Overview > Debugging" in chunk["text"] for chunk in chunks)


def test_long_chunk_splitting_respects_max_chars_approximately() -> None:
    text = "Paragraph one. " * 120
    chunks = split_long_text(text, max_chars=300, overlap_chars=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_issue_chunk_includes_title_body_and_metadata() -> None:
    record = {
        "repo": "nodejs/node",
        "issue_number": 9001,
        "url": "https://github.com/nodejs/node/issues/9001",
        "title": "https.request leaks memory",
        "body": "Repro: send many requests. Actual: heap keeps growing.",
        "created_at": "2016-09-01T00:00:00Z",
        "closed_at": "2016-09-02T00:00:00Z",
        "label": "bug",
    }
    chunks = chunk_issue_record(record, source_split="test", max_chars=500)
    assert chunks
    assert "Issue: https.request leaks memory" in chunks[0]["text"]
    assert "Resolved issue corpus currently uses issue title/body only until comments are fetched." in chunks[0]["text"]

    rows = build_issue_corpus_rows([record], source_split="test", max_chars=500)
    validate_corpus_row(rows[0])
    assert rows[0]["metadata"]["issue_number"] == 9001
    assert rows[0]["metadata"]["label"] == "bug"


def test_nested_docs_are_discovered_and_doc_chunks_are_tagged(tmp_path) -> None:
    docs_dir = tmp_path / "node_docs"
    api_dir = docs_dir / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "http.md").write_text(
        "# HTTP\nIntro\n\n## request\nUse `https.request()` for client calls.\n",
        encoding="utf-8",
    )
    (docs_dir / "globals.md").write_text("# Globals\nReference text.\n", encoding="utf-8")

    paths = discover_doc_paths(docs_dir)
    assert [path.relative_to(docs_dir).as_posix() for path in paths] == ["api/http.md", "globals.md"]

    rows = build_doc_corpus_rows(docs_dir, max_chars=240)
    assert rows
    assert all(row["source_type"] == "doc" for row in rows)
    assert all(row["metadata"]["path"] in {"api/http.md", "globals.md"} for row in rows)
    assert any(row["metadata"]["section"] == "HTTP > request" for row in rows)


def test_duplicate_nested_docs_are_deduplicated(tmp_path) -> None:
    docs_dir = tmp_path / "node_docs"
    (docs_dir / "api").mkdir(parents=True)
    (docs_dir / "api" / "api").mkdir(parents=True)
    content = "# HTTP\n\n## request\nUse `https.request()`.\n"
    (docs_dir / "api" / "http.md").write_text(content, encoding="utf-8")
    (docs_dir / "api" / "api" / "http.md").write_text(content, encoding="utf-8")

    assert collapse_redundant_leading_segment("api/api/http.md") == "api/http.md"

    paths = discover_doc_paths(docs_dir)
    assert [path.relative_to(docs_dir).as_posix() for path in paths] == ["api/http.md"]
