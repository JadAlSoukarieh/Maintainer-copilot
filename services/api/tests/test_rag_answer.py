from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from maintcopilot_api.api.routes.rag import answer_rag_question
from maintcopilot_api.domain.rag import RagAnswerRequest
from maintcopilot_api.services.rag.rag_service import RagService


def _mock_request() -> MagicMock:
    req = MagicMock()
    req.app.state.minio_client = None
    return req


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
    assert "Based on the local Node.js knowledge base" in response.answer
    assert "corpus" not in response.answer.lower()


def test_rag_answer_docs_template_uses_supported_behavior(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    text = "stream.pipeline() calls stream.destroy(err) on all streams after a pipeline error, and it waits for cleanup before invoking the callback."
    corpus_path.write_text(json.dumps(_row("doc-stream", "doc", text, title="stream.pipeline")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="Where do the Node docs explain stream pipeline cleanup after errors?", retriever="sparse", top_k=1)
    )

    assert "the relevant API documentation is `stream.pipeline`" in response.answer
    assert "The stream docs say `stream.pipeline()`" in response.answer
    assert "stream.destroy(err)" in response.answer


def test_rag_answer_dns_docs_prefer_dns_error_codes_over_generic_errors(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    rows = [
        _row(
            "doc-errors",
            "doc",
            "Errors > Node.js error codes > ERR_DNS_SET_SERVERS_FAILED. c-ares failed to set the DNS server.",
            title="errors",
        ),
        _row(
            "doc-dns",
            "doc",
            "DNS > Error codes. Each DNS query can return one of the following error codes: dns.NODATA and dns.TIMEOUT.",
            title="dns",
        ),
    ]
    corpus_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(
            question="Where do the Node.js DNS docs list resolver error codes such as dns.NODATA and dns.TIMEOUT?",
            retriever="sparse",
            top_k=2,
        )
    )

    assert "the relevant API documentation is `dns`" in response.answer
    assert "error codes" in response.answer.lower()
    assert "the relevant API documentation is `errors`" not in response.answer


def test_rag_answer_route_includes_citations_and_rewritten_query(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("issue-memory", "resolved_issue", "Memory leak in HTTPS request issue.")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = answer_rag_question(
        _mock_request(),
        RagAnswerRequest(question="How do I debug a memory leak in https request?", retriever="sparse", top_k=1),
        rag_service=service,
    )

    assert response.citations[0].chunk_id == "issue-memory"
    assert response.rewritten_query != response.question
    assert response.diagnostics.query_rewrite_enabled is True


def test_rag_answer_does_not_concatenate_raw_titles_only(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    rows = [
        _row(
            "issue-memory-1",
            "resolved_issue",
            "Issue: Memory leak for https.request() on ECONNRESET\nProblem: Repeated requests grow RSS after ECONNRESET. Maintainers discuss reproducing the socket lifecycle and cleanup behavior.",
            title="Memory leak for https.request() on ECONNRESET",
        ),
        _row(
            "issue-memory-2",
            "resolved_issue",
            "Issue: Massive memory leak in HTTP upgrade event\nProblem: The upgrade path was reported with sustained memory growth when sockets were not cleaned up as expected.",
            title="Massive memory leak in HTTP upgrade event",
        ),
    ]
    corpus_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="How do I debug a memory leak in https request?", retriever="sparse", top_k=2)
    )

    assert response.answer.startswith("Based on the local Node.js knowledge base")
    assert "The strongest cited issues include" in response.answer
    assert "ECONNRESET Massive memory leak" not in response.answer
    assert "corpus" not in response.answer.lower()
    assert "guaranteed root cause" not in response.answer.lower()


def test_rag_answer_skips_breadcrumb_list_and_header_fragments(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    text = "\n".join(
        [
            "Issue: stream",
            "Stream > Consumers > pipeline:",
            "* raw list fragment",
            "Node: 20.0.0",
            "Problem: stream.pipeline() destroys streams when an error interrupts the pipeline and cleanup must happen across each stream.",
        ]
    )
    corpus_path.write_text(json.dumps(_row("doc-stream", "doc", text, title="stream")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="Where do the Node docs explain stream pipeline cleanup after errors?", retriever="sparse", top_k=1)
    )

    assert "local Node.js knowledge base" in response.answer
    assert "Stream > Consumers" not in response.answer
    assert "raw list fragment" not in response.answer
    assert "Node: 20.0.0" not in response.answer


def test_rag_answer_filters_internal_implementation_notes(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    text = "\n".join(
        [
            "Resolved issue corpus currently uses issue title/body only until comments are fetched.",
            "Resolution note: this is an internal ingestion warning.",
            "tls.createServer secureOptions issue reports missing behavior details in the docs.",
        ]
    )
    corpus_path.write_text(json.dumps(_row("issue-tls", "resolved_issue", text, title="tls.createServer secureOptions")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="Which resolved issue discusses tls.createServer secureOptions?", retriever="sparse", top_k=1)
    )

    lowered = response.answer.lower()
    assert "corpus currently uses" not in lowered
    assert "until comments are fetched" not in lowered
    assert "corpus" not in lowered


def test_rag_answer_debug_template_avoids_fix_language(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    rows = [
        _row(
            "issue-memory-1",
            "resolved_issue",
            "Repeated requests grow RSS after ECONNRESET and maintainers compare socket cleanup and request lifecycle behavior.",
            title="Memory leak for https.request() on ECONNRESET",
        ),
        _row(
            "issue-memory-2",
            "resolved_issue",
            "HTTP upgrade handling was reported with sustained memory growth when the socket path was not cleaned up as expected.",
            title="Massive memory leak in HTTP upgrade event",
        ),
    ]
    corpus_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="How do I debug a memory leak in https request?", retriever="sparse", top_k=2)
    )

    assert "related issue evidence points to similar symptoms" in response.answer.lower()
    assert "The strongest cited issues include" in response.answer
    assert "fix" not in response.answer.lower()
    assert "root cause" not in response.answer.lower()


def test_rag_answer_stream_pipeline_includes_destroy_and_exceptions(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    text = (
        "stream.pipeline() will call stream.destroy(err) on all streams except Readable streams which have emitted "
        "'end' or 'close' and Writable streams which have emitted 'finish' or 'close'."
    )
    corpus_path.write_text(json.dumps(_row("doc-stream", "doc", text, title="stream")) + "\n", encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="How does stream.pipeline() clean up streams when a pipeline fails?", retriever="sparse", top_k=1)
    )

    lowered = response.answer.lower()
    assert "stream.pipeline()" in response.answer
    assert "destroy(err)" in response.answer
    assert "except" in lowered
    assert ("readable" in lowered and ("end" in lowered or "close" in lowered))
    assert ("writable" in lowered and ("finish" in lowered or "close" in lowered))


def test_rag_answer_dedupes_citations_by_title_and_caps_excerpts(tmp_path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    long_text = "Issue: Duplicate memory leak\nProblem: " + ("memory leak https request cleanup " * 40)
    rows = [
        _row("issue-1", "resolved_issue", long_text, title="Duplicate memory leak"),
        _row("issue-2", "resolved_issue", long_text, title="Duplicate memory leak"),
        _row("issue-3", "resolved_issue", "Issue: TLS RSS growth\nProblem: tls memory leak request cleanup", title="TLS RSS growth"),
    ]
    corpus_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    service = RagService(corpus_path=corpus_path, embedding_index_dir=tmp_path / "embeddings")

    response = service.answer_rag_question(
        RagAnswerRequest(question="memory leak https request cleanup", retriever="sparse", top_k=5)
    )

    titles = [citation.title for citation in response.citations]
    assert titles.count("Duplicate memory leak") == 1
    assert all(len(citation.text_excerpt) <= 300 for citation in response.citations)


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


def test_rag_answer_falls_back_to_sparse_when_dense_query_path_is_unavailable(monkeypatch, tmp_path: Path) -> None:
    corpus_path = tmp_path / "rag_corpus.jsonl"
    corpus_path.write_text(json.dumps(_row("doc-http", "doc", "HTTP docs explain ClientRequest behavior.")) + "\n", encoding="utf-8")
    embedding_dir = _write_tiny_embedding_index(tmp_path, ["doc-http"])
    service = RagService(
        corpus_path=corpus_path,
        embedding_index_dir=embedding_dir,
        reranker_model_path=tmp_path / "missing-reranker-model",
        rerank_top_n=20,
    )

    monkeypatch.setattr(
        "maintcopilot_api.services.rag.retrieval.DenseRetriever.query",
        lambda self, query_text, top_k=5: (_ for _ in ()).throw(RuntimeError("dense unavailable")),
    )

    response = service.answer_rag_question(RagAnswerRequest(question="Where do docs explain https request?", top_k=1))

    assert response.retriever == "sparse"
    assert response.diagnostics.requested_retriever == "reranked"
    assert response.diagnostics.effective_retriever == "sparse"
    assert response.diagnostics.fallback_reason == "dense_retriever_unavailable"
    assert response.citations


def _row(chunk_id: str, source_type: str, text: str, *, title: str | None = None) -> dict:
    return {
        "chunk_id": chunk_id,
        "source_type": source_type,
        "source_id": chunk_id,
        "title": title or chunk_id,
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
