from __future__ import annotations

import json

import numpy as np
import pytest

from maintcopilot_api.services.rag.corpus import build_doc_corpus_rows, build_issue_corpus_rows, validate_corpus_row
from maintcopilot_api.services.rag.retrieval import (
    CrossEncoderReranker,
    DenseRetriever,
    HybridRetriever,
    RerankedRetriever,
    SparseRetriever,
    apply_metadata_boost,
    filter_corpus_rows,
)
from maintcopilot_api.services.rag.query_transform import rewrite_query


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


def test_dense_retriever_loads_tiny_embedding_index(tmp_path) -> None:
    rows = [
        _toy_row("a", "doc", "HTTP request lifecycle debugging"),
        _toy_row("b", "resolved_issue", "zlib memory leak issue"),
    ]
    index_dir = tmp_path / "embeddings"
    index_dir.mkdir()
    np.savez_compressed(index_dir / "dense_index.npz", embeddings=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    (index_dir / "chunk_ids.json").write_text(json.dumps(["a", "b"]), encoding="utf-8")

    retriever = DenseRetriever(rows, index_dir=index_dir, query_encoder=lambda texts: np.array([[0.0, 1.0]], dtype=np.float32))
    results = retriever.query("memory leak", top_k=2)

    assert [result["chunk_id"] for result in results] == ["b", "a"]


def test_hybrid_alpha_one_behaves_like_sparse_ordering(tmp_path) -> None:
    rows = [
        _toy_row("sparse-winner", "doc", "http http http request docs"),
        _toy_row("dense-winner", "doc", "unrelated semantic result"),
    ]
    dense = _toy_dense_retriever(tmp_path, rows, query_vector=np.array([[0.0, 1.0]], dtype=np.float32))
    sparse = SparseRetriever(rows)
    hybrid = HybridRetriever(sparse, dense, alpha=1.0)

    assert hybrid.query("http request", top_k=2)[0]["chunk_id"] == sparse.query("http request", top_k=2)[0]["chunk_id"]


def test_hybrid_alpha_zero_behaves_like_dense_ordering(tmp_path) -> None:
    rows = [
        _toy_row("sparse-winner", "doc", "http http http request docs"),
        _toy_row("dense-winner", "doc", "unrelated semantic result"),
    ]
    dense = _toy_dense_retriever(tmp_path, rows, query_vector=np.array([[0.0, 1.0]], dtype=np.float32))
    sparse = SparseRetriever(rows)
    hybrid = HybridRetriever(sparse, dense, alpha=0.0)

    assert hybrid.query("http request", top_k=2)[0]["chunk_id"] == dense.query("http request", top_k=2)[0]["chunk_id"]


def test_hybrid_scoring_combines_sparse_and_dense(tmp_path) -> None:
    rows = [
        _toy_row("sparse-only", "doc", "http request request request"),
        _toy_row("dense-only", "doc", "semantic match"),
        _toy_row("both", "doc", "http request"),
    ]
    index_dir = tmp_path / "hybrid_embeddings"
    index_dir.mkdir()
    np.savez_compressed(
        index_dir / "dense_index.npz",
        embeddings=np.array([[0.0, 0.1], [0.0, 1.0], [0.0, 0.8]], dtype=np.float32),
    )
    (index_dir / "chunk_ids.json").write_text(json.dumps(["sparse-only", "dense-only", "both"]), encoding="utf-8")

    sparse = SparseRetriever(rows)
    dense = DenseRetriever(rows, index_dir=index_dir, query_encoder=lambda texts: np.array([[0.0, 1.0]], dtype=np.float32))
    hybrid = HybridRetriever(sparse, dense, alpha=0.5)
    results = hybrid.query("http request", top_k=3)

    assert results[0]["chunk_id"] == "both"
    assert "sparse_score" in results[0]
    assert "dense_score" in results[0]


def test_reranker_preserves_candidate_set_and_reorders_by_score() -> None:
    candidates = [
        _result("a", 0.9, "alpha"),
        _result("b", 0.8, "beta"),
        _result("c", 0.7, "gamma"),
    ]
    base = _StaticRetriever(candidates)
    reranker = CrossEncoderReranker(scorer=lambda pairs: [0.2, 0.9, 0.5])
    retriever = RerankedRetriever(base, reranker, rerank_top_n=3)

    results = retriever.query("query", top_k=3)

    assert {item["chunk_id"] for item in results} == {"a", "b", "c"}
    assert [item["chunk_id"] for item in results] == ["b", "c", "a"]
    assert results[0]["original_score"] == 0.8
    assert results[0]["reranker_score"] == pytest.approx(0.9)
    assert results[0]["final_rank"] == 1


def test_reranked_retriever_returns_top_k_after_reranking() -> None:
    candidates = [
        _result("a", 0.9, "alpha"),
        _result("b", 0.8, "beta"),
        _result("c", 0.7, "gamma"),
    ]
    base = _StaticRetriever(candidates)
    reranker = CrossEncoderReranker(scorer=lambda pairs: [0.2, 0.9, 0.5])
    retriever = RerankedRetriever(base, reranker, rerank_top_n=3)

    results = retriever.query("query", top_k=2)

    assert [item["chunk_id"] for item in results] == ["b", "c"]


def test_metadata_boost_increases_preferred_source_type_score() -> None:
    rewrite = rewrite_query("How do I debug a memory leak in https request?")
    results = [
        _result("doc-http", 0.8, "HTTP request docs"),
        _result("issue-memory", 0.78, "Memory leak in HTTPS issue"),
    ]
    results[0]["source_type"] = "doc"
    results[1]["source_type"] = "resolved_issue"

    boosted = apply_metadata_boost(results, rewrite, boost_amount=0.08)

    assert boosted[0]["chunk_id"] == "issue-memory"
    assert boosted[0]["original_score"] == 0.78
    assert boosted[0]["metadata_boost"] > 0
    assert boosted[0]["final_score"] == boosted[0]["score"]


def test_source_type_filter_returns_only_matching_rows() -> None:
    rows = [_toy_row("doc-1", "doc", "docs"), _toy_row("issue-1", "resolved_issue", "issue")]

    docs = filter_corpus_rows(rows, "doc")
    issues = filter_corpus_rows(rows, "resolved_issue")

    assert [row["source_type"] for row in docs] == ["doc"]
    assert [row["source_type"] for row in issues] == ["resolved_issue"]


def _toy_dense_retriever(tmp_path, rows: list[dict], *, query_vector: np.ndarray) -> DenseRetriever:
    index_dir = tmp_path / "embeddings"
    index_dir.mkdir(exist_ok=True)
    np.savez_compressed(index_dir / "dense_index.npz", embeddings=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    (index_dir / "chunk_ids.json").write_text(json.dumps([row["chunk_id"] for row in rows]), encoding="utf-8")
    return DenseRetriever(rows, index_dir=index_dir, query_encoder=lambda texts: query_vector)


def _result(chunk_id: str, score: float, text: str) -> dict:
    row = _toy_row(chunk_id, "doc", text)
    return {
        "chunk_id": row["chunk_id"],
        "score": score,
        "source_type": row["source_type"],
        "title": row["title"],
        "url": row["url"],
        "text": row["text"],
        "metadata": row["metadata"],
    }


class _StaticRetriever:
    def __init__(self, results: list[dict]) -> None:
        self.results = results

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        return self.results[:top_k]


def _toy_row(chunk_id: str, source_type: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "source_type": source_type,
        "source_id": chunk_id,
        "title": chunk_id,
        "url": "",
        "text": text,
        "metadata": {
            "repo": "nodejs/node",
            "source_split": "docs" if source_type == "doc" else "test",
            "label": None,
            "issue_number": None,
            "created_at": None,
            "closed_at": None,
            "path": "api/test.md",
            "section": "test",
        },
    }
