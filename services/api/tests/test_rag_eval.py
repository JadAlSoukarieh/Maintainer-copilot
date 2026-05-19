from __future__ import annotations

from pathlib import Path

from maintcopilot_api.services.rag.eval import compute_retrieval_metrics, run_rag_retrieval_eval
from maintcopilot_api.services.rag.retrieval import CrossEncoderReranker


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


def test_retrieval_eval_report_records_rewrite_and_boost_flags(tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    golden_path = tmp_path / "rag_golden.jsonl"
    thresholds_path = tmp_path / "thresholds.yaml"
    report_path = tmp_path / "rag_eval_sparse_rewrite_boost.json"

    corpus_row = {
        "chunk_id": "issue-memory-001",
        "source_type": "resolved_issue",
        "source_id": "1",
        "title": "Memory leak in HTTPS request",
        "url": "",
        "text": "This resolved issue discusses a memory leak in the HTTPS request path.",
        "metadata": {
            "repo": "nodejs/node",
            "source_split": "test",
            "label": "bug",
            "issue_number": 1,
            "created_at": None,
            "closed_at": None,
            "path": None,
            "section": "issue_record",
        },
    }
    golden_row = {
        "golden_id": "rag-golden-001",
        "question": "How do I debug a memory leak in https request?",
        "ideal_answer": "Use the memory leak issue context.",
        "ground_truth_chunk_ids": ["issue-memory-001"],
        "source_type": "resolved_issue",
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
        query_rewrite_enabled=True,
        metadata_boost_enabled=True,
    )

    assert exit_code == 0
    assert result["query_rewrite_enabled"] is True
    assert result["metadata_boost_enabled"] is True
    assert result["metrics"]["details"][0]["query_text"] != golden_row["question"]


def test_reranked_eval_report_includes_reranker_fields(tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    golden_path = tmp_path / "rag_golden.jsonl"
    thresholds_path = tmp_path / "thresholds.yaml"
    report_path = tmp_path / "rag_eval_reranked.json"
    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    corpus_rows = [
        {
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
        },
        {
            "chunk_id": "doc-other-001",
            "source_type": "doc",
            "source_id": "api/other.md#other:001",
            "title": "other",
            "url": "",
            "text": "Other docs.",
            "metadata": {
                "repo": "nodejs/node",
                "source_split": "docs",
                "label": None,
                "issue_number": None,
                "created_at": None,
                "closed_at": None,
                "path": "api/other.md",
                "section": "Other",
            },
        },
    ]
    golden_row = {
        "golden_id": "rag-golden-001",
        "question": "What docs explain HTTP request debugging?",
        "ideal_answer": "Use the HTTP request docs.",
        "ground_truth_chunk_ids": ["doc-http-001"],
        "source_type": "doc",
        "needs_human_review": False,
        "human_review_status": "ai_assisted_approved",
    }
    corpus_path.write_text("\n".join(__import__("json").dumps(row) for row in corpus_rows) + "\n", encoding="utf-8")
    golden_path.write_text("\n".join(__import__("json").dumps(golden_row) for _ in range(25)) + "\n", encoding="utf-8")
    thresholds_path.write_text("rag_retrieval:\n  min_hit_at_5: 0.4\n  min_mrr_at_10: 0.2\n", encoding="utf-8")
    __import__("numpy").savez_compressed(
        embedding_dir / "dense_index.npz",
        embeddings=__import__("numpy").array([[1.0, 0.0], [0.0, 1.0]], dtype=__import__("numpy").float32),
    )
    (embedding_dir / "chunk_ids.json").write_text(__import__("json").dumps(["doc-http-001", "doc-other-001"]), encoding="utf-8")

    reranker = CrossEncoderReranker(scorer=lambda pairs: [0.9 - (0.1 * index) for index, _pair in enumerate(pairs)])
    exit_code, result = run_rag_retrieval_eval(
        corpus_path=corpus_path,
        golden_path=golden_path,
        thresholds_path=thresholds_path,
        report_path=report_path,
        retriever_type="reranked",
        embedding_index_dir=embedding_dir,
        alpha=0.5,
        base_retriever_type="sparse",
        rerank_top_n=2,
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        reranker=reranker,
    )

    assert exit_code == 0
    assert result["retriever"] == "reranked"
    assert result["base_retriever"] == "sparse"
    assert result["rerank_top_n"] == 2
    assert result["reranker_model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert report_path.exists()
