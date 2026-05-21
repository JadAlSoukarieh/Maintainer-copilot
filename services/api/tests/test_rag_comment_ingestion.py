from __future__ import annotations

from maintcopilot_api.services.rag.chunking import chunk_issue_comment_record
from maintcopilot_api.services.rag.corpus import (
    build_issue_comment_corpus_rows,
    load_jsonl_records,
)


def test_issue_comment_chunking_preserves_metadata() -> None:
    record = {
        "issue_number": 9001,
        "comment_id": 77,
        "author_login": "maintainer",
        "author_association": "MEMBER",
        "created_at": "2026-05-21T00:00:00Z",
        "body": "This looks related to socket cleanup after ECONNRESET.",
        "url": "https://github.com/nodejs/node/issues/9001#issuecomment-77",
        "is_possible_maintainer": True,
    }

    chunks = chunk_issue_comment_record(record, source_split="issue_comments", max_chars=300)

    assert chunks
    assert "Issue comment for #9001" in chunks[0]["text"]
    assert chunks[0]["metadata"]["author_association"] == "MEMBER"
    assert chunks[0]["metadata"]["comment_id"] == 77


def test_issue_comment_rows_are_optional_when_file_missing(tmp_path) -> None:
    missing = tmp_path / "missing.jsonl"
    records = load_jsonl_records(missing)

    rows = build_issue_comment_corpus_rows(records, source_split="issue_comments")

    assert records == []
    assert rows == []


def test_issue_comment_rows_are_included_when_present() -> None:
    record = {
        "repo": "nodejs/node",
        "issue_number": 9001,
        "comment_id": 77,
        "author_login": "maintainer",
        "author_association": "MEMBER",
        "created_at": "2026-05-21T00:00:00Z",
        "body": "This looks related to socket cleanup after ECONNRESET.",
        "url": "https://github.com/nodejs/node/issues/9001#issuecomment-77",
        "is_possible_maintainer": True,
    }

    rows = build_issue_comment_corpus_rows([record], source_split="issue_comments")

    assert rows
    assert rows[0]["source_type"] == "issue_comment"
    assert rows[0]["metadata"]["comment_id"] == 77
    assert rows[0]["metadata"]["is_possible_maintainer"] is True
