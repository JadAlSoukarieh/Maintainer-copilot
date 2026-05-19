from __future__ import annotations

from maintcopilot_api.services.rag.golden import generate_rag_golden_candidates, validate_rag_golden


def test_candidate_generation_uses_existing_chunk_ids() -> None:
    corpus_rows = []
    for index in range(12):
        corpus_rows.append(
            {
                "chunk_id": f"doc-{index:03d}",
                "source_type": "doc",
                "source_id": f"api/doc-{index}.md#section:001",
                "title": f"doc-{index}",
                "url": "",
                "text": f"Document: doc-{index}\nSection path: Topic {index}\n\nThis section explains HTTP request debugging and memory diagnostics for case {index}.",
                "metadata": {
                    "repo": "nodejs/node",
                    "source_split": "docs",
                    "label": None,
                    "issue_number": None,
                    "created_at": None,
                    "closed_at": None,
                    "path": f"api/doc-{index}.md",
                    "section": f"Topic {index}",
                },
            }
        )
    for index in range(13):
        corpus_rows.append(
            {
                "chunk_id": f"issue-{index:03d}",
                "source_type": "resolved_issue",
                "source_id": str(index),
                "title": f"Issue title {index}",
                "url": f"https://github.com/nodejs/node/issues/{index}",
                "text": f"Issue: Issue title {index}\n\nProblem:\nThis resolved issue discusses memory leak debugging for HTTP upgrade path {index}.",
                "metadata": {
                    "repo": "nodejs/node",
                    "source_split": "test",
                    "label": "bug",
                    "issue_number": index,
                    "created_at": "2016-01-01T00:00:00Z",
                    "closed_at": "2016-01-02T00:00:00Z",
                    "path": None,
                    "section": "issue_record",
                },
            }
        )

    candidates = generate_rag_golden_candidates(corpus_rows)
    existing_ids = {row["chunk_id"] for row in corpus_rows}
    assert len(candidates) == 25
    assert all(candidate["ground_truth_chunk_ids"][0] in existing_ids for candidate in candidates)


def test_validator_rejects_missing_chunk_ids() -> None:
    corpus_rows = [{"chunk_id": "doc-001", "source_type": "doc", "source_id": "doc", "title": "doc", "url": "", "text": "x", "metadata": {"repo": "nodejs/node", "source_split": "docs", "label": None, "issue_number": None, "created_at": None, "closed_at": None, "path": "api/doc.md", "section": "Doc"}}]
    golden_rows = [
        {
            "golden_id": "rag-golden-001",
            "question": "What docs explain x?",
            "ideal_answer": "x",
            "ground_truth_chunk_ids": ["missing"],
            "source_type": "doc",
            "source_titles": ["doc"],
            "needs_human_review": True,
            "review_notes": "review",
        }
    ]
    result = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows)
    assert not result["ok"]
    assert any("unknown ground_truth_chunk_id" in error for error in result["errors"])


def test_validator_rejects_final_file_with_review_flags() -> None:
    corpus_rows = [{"chunk_id": "doc-001", "source_type": "doc", "source_id": "doc", "title": "doc", "url": "", "text": "x", "metadata": {"repo": "nodejs/node", "source_split": "docs", "label": None, "issue_number": None, "created_at": None, "closed_at": None, "path": "api/doc.md", "section": "Doc"}}]
    golden_rows = [
        {
            "golden_id": f"rag-golden-{index:03d}",
            "question": "Q",
            "ideal_answer": "A",
            "ground_truth_chunk_ids": ["doc-001"],
            "source_type": "doc",
            "source_titles": ["doc"],
            "needs_human_review": True,
            "review_notes": "review",
        }
        for index in range(1, 26)
    ]
    result = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows, require_final=True)
    assert not result["ok"]
    assert any("needs_human_review=false" in error for error in result["errors"])
