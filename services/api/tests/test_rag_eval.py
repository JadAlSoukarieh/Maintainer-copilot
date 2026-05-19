from __future__ import annotations

from pathlib import Path

from maintcopilot_api.services.rag.eval import compute_retrieval_metrics, run_rag_retrieval_eval


def test_retrieval_eval_computes_hit_and_mrr() -> None:
    corpus_rows = [
        {
            "chunk_id": "doc-http-001",
            "source_type": "doc",
            "source_id": "api/http.md#http:001",
            "title": "http",
            "url": "",
            "text": "Document: http\nSection path: HTTP > request\n\nHTTP request docs explain how to handle request lifecycle and debugging.",
            "metadata": {
                "repo": "nodejs/node",
                "source_split": "docs",
                "label": None,
                "issue_number": None,
                "created_at": None,
                "closed_at": None,
                "path": "api/http.md",
                "section": "HTTP > request",
            },
        },
        {
            "chunk_id": "issue-001",
            "source_type": "resolved_issue",
            "source_id": "1",
            "title": "Memory leak in HTTP upgrade",
            "url": "https://github.com/nodejs/node/issues/1",
            "text": "Issue: Memory leak in HTTP upgrade\n\nProblem:\nThis resolved issue discusses a memory leak in the HTTP upgrade path.",
            "metadata": {
                "repo": "nodejs/node",
                "source_split": "test",
                "label": "bug",
                "issue_number": 1,
                "created_at": "2016-01-01T00:00:00Z",
                "closed_at": "2016-01-02T00:00:00Z",
                "path": None,
                "section": "issue_record",
            },
        },
    ]
    golden_rows = [
        {
            "golden_id": "rag-golden-001",
            "question": "What docs explain HTTP request debugging?",
            "ideal_answer": "Use the HTTP request docs.",
            "ground_truth_chunk_ids": ["doc-http-001"],
            "source_type": "doc",
        },
        {
            "golden_id": "rag-golden-002",
            "question": "What resolved issue discusses memory leak in HTTP upgrade?",
            "ideal_answer": "The memory leak in HTTP upgrade issue.",
            "ground_truth_chunk_ids": ["issue-001"],
            "source_type": "resolved_issue",
        },
    ]
    metrics = compute_retrieval_metrics(golden_rows, corpus_rows)
    assert metrics["hit_at_5"] == 1.0
    assert metrics["mrr_at_10"] == 1.0


def test_retrieval_eval_missing_final_golden_returns_clear_error(tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text("", encoding="utf-8")
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text("rag_retrieval:\n  min_hit_at_5: 0.4\n  min_mrr_at_10: 0.2\n", encoding="utf-8")
    report_path = tmp_path / "rag_eval_report.json"

    exit_code, result = run_rag_retrieval_eval(
        corpus_path=corpus_path,
        golden_path=tmp_path / "missing.jsonl",
        thresholds_path=thresholds_path,
        report_path=report_path,
    )
    assert exit_code == 1
    assert "Run python scripts/make_rag_golden_candidates.py" in result["message"]


def test_retrieval_eval_report_includes_retriever_type(tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    golden_path = tmp_path / "rag_golden.jsonl"
    thresholds_path = tmp_path / "thresholds.yaml"
    report_path = tmp_path / "rag_eval_sparse.json"

    corpus_row = {
        "chunk_id": "doc-http-001",
        "source_type": "doc",
        "source_id": "api/http.md#http:001",
        "title": "http",
        "url": "",
        "text": "HTTP request docs explain request debugging.",
        "metadata": {
            "repo": "nodejs/node",
            "source_split": "docs",
            "label": None,
            "issue_number": None,
            "created_at": None,
            "closed_at": None,
            "path": "api/http.md",
            "section": "HTTP > request",
        },
    }
    golden_row = {
        "golden_id": "rag-golden-001",
        "question": "What docs explain HTTP request debugging?",
        "ideal_answer": "Use the HTTP request docs.",
        "ground_truth_chunk_ids": ["doc-http-001"],
        "source_type": "doc",
        "needs_human_review": False,
        "human_review_status": "ai_assisted_approved",
    }
    corpus_path.write_text(f"{__import__('json').dumps(corpus_row)}\n", encoding="utf-8")
    golden_path.write_text("\n".join(__import__("json").dumps(golden_row) for _ in range(25)) + "\n", encoding="utf-8")
    thresholds_path.write_text("rag_retrieval:\n  min_hit_at_5: 0.4\n  min_mrr_at_10: 0.2\n", encoding="utf-8")

    exit_code, result = run_rag_retrieval_eval(
        corpus_path=corpus_path,
        golden_path=golden_path,
        thresholds_path=thresholds_path,
        report_path=report_path,
        retriever_type="sparse",
    )

    assert exit_code == 0
    assert result["retriever"] == "sparse"
    assert report_path.exists()
