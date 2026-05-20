from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from maintcopilot_api.api.routes.rag import answer_rag_question
from maintcopilot_api.domain.rag import RagAnswerRequest
from maintcopilot_api.services.rag.rag_service import RagService


def test_rag_answer_returns_schema_valid_response(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("doc-http", "doc", "HTTP docs explain ClientRequest behavior.")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(
            question="Where do docs explain https request?",
            retriever="sparse",
            top_k=1,
        )
    )

    assert response.method == "extractive_rag"
    assert response.citations
    assert response.rewritten_query != response.question
    assert "retrieved local corpus chunks" in response.answer


def test_rag_answer_route_includes_citations_and_rewritten_query(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("issue-memory", "resolved_issue", "Memory leak in HTTPS request issue.")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = answer_rag_question(
        RagAnswerRequest(question="How do I debug a memory leak in https request?", retriever="sparse", top_k=1),
        rag_service=service,
    )

    assert response.citations[0].chunk_id == "issue-memory"
    assert response.rewritten_query != response.question
    assert response.diagnostics.query_rewrite_enabled is True


def test_rag_answer_uses_reranked_when_model_path_exists(monkeypatch, tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("doc-http", "doc", "HTTP docs explain ClientRequest behavior.")) + "\n", encoding="utf-8")
    embedding_dir = _write_tiny_embedding_index(tmp_path, ["doc-http"])
    reranker_dir = tmp_path / "reranker_model"
    reranker_dir.mkdir()

    monkeypatch.setattr(
        "maintcopilot_api.services.rag.rag_service.CrossEncoderReranker.score",
        lambda self, query_text, candidates: [1.0 for _candidate in candidates],
    )

    service = RagService(
        corpus_path=corpus_path,
        embedding_index_dir=embedding_dir,
        reranker_model_path=reranker_dir,
        rerank_top_n=20,
    )
    response = service.answer_rag_question(RagAnswerRequest(question="Where do docs explain https request?", top_k=1))

    assert response.retriever == "reranked"
    assert response.diagnostics.requested_retriever == "reranked"
    assert response.diagnostics.effective_retriever == "reranked"
    assert response.diagnostics.fallback_reason is None


def test_rag_answer_falls_back_to_hybrid_when_reranker_model_missing(tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("doc-http", "doc", "HTTP docs explain ClientRequest behavior.")) + "\n", encoding="utf-8")
    embedding_dir = _write_tiny_embedding_index(tmp_path, ["doc-http"])
    service = RagService(
        corpus_path=corpus_path,
        embedding_index_dir=embedding_dir,
        reranker_model_path=tmp_path / "missing-reranker-model",
        rerank_top_n=20,
    )

    response = service.answer_rag_question(RagAnswerRequest(question="Where do docs explain https request?", top_k=1))

    assert response.retriever == "hybrid"
    assert response.diagnostics.requested_retriever == "reranked"
    assert response.diagnostics.effective_retriever == "hybrid"
    assert response.diagnostics.fallback_reason == "reranker_model_missing"


def _row(chunk_id: str, source_type: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "source_type": source_type,
        "source_id": chunk_id,
        "title": chunk_id,
        "url": "https://github.com/nodejs/node",
        "text": text,
        "metadata": {
            "repo": "nodejs/node",
            "source_split": "docs" if source_type == "doc" else "test",
            "label": None,
            "issue_number": None,
            "created_at": None,
            "closed_at": None,
            "path": "api/http.md" if source_type == "doc" else None,
            "section": "HTTP",
        },
    }


def _write_tiny_embedding_index(tmp_path: Path, chunk_ids: list[str]) -> Path:
    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()
    embeddings = np.zeros((len(chunk_ids), 384), dtype=np.float32)
    embeddings[:, 0] = 1.0
    np.savez_compressed(
        embedding_dir / "dense_index.npz",
        embeddings=embeddings,
    )
    (embedding_dir / "chunk_ids.json").write_text(json.dumps(chunk_ids), encoding="utf-8")
    return embedding_dir
