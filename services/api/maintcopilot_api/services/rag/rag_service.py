from __future__ import annotations

import re
from pathlib import Path

from maintcopilot_api.domain.rag import (
    QueryRewriteResult,
    RagAnswerDiagnostics,
    RagAnswerRequest,
    RagAnswerResponse,
    RagCitation,
)
from maintcopilot_api.services.rag.query_transform import rewrite_query
from maintcopilot_api.services.rag.retrieval import (
    DenseRetriever,
    HybridRetriever,
    SparseRetriever,
    apply_metadata_boost,
    filter_corpus_rows,
    load_corpus_rows,
)


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class RagService:
    def __init__(self, *, corpus_path: Path, embedding_index_dir: Path) -> None:
        self.corpus_path = Path(corpus_path)
        self.embedding_index_dir = Path(embedding_index_dir)
        self._corpus_rows: list[dict] | None = None

    def answer_rag_question(self, request: RagAnswerRequest) -> RagAnswerResponse:
        rewrite_result = (
            rewrite_query(request.question)
            if request.query_rewrite
            else QueryRewriteResult(
                original_query=request.question,
                rewritten_query=request.question,
                added_terms=[],
                intent="unknown",
                preferred_source_type=None,
            )
        )
        rows = filter_corpus_rows(self._load_rows(), request.source_type)
        retriever = self._build_retriever(request.retriever, rows, alpha=request.alpha)
        results = retriever.query(rewrite_result.rewritten_query, top_k=request.top_k)
        if request.metadata_boost:
            results = apply_metadata_boost(results, rewrite_result)
        citations = [_citation_from_result(result) for result in results[: request.top_k]]
        answer = _build_extractive_answer(results[: min(3, request.top_k)])
        return RagAnswerResponse(
            answer=answer,
            question=request.question,
            rewritten_query=rewrite_result.rewritten_query,
            intent=rewrite_result.intent,
            retriever=request.retriever,
            alpha=request.alpha,
            citations=citations,
            diagnostics=RagAnswerDiagnostics(
                query_rewrite_enabled=request.query_rewrite,
                metadata_boost_enabled=request.metadata_boost,
                preferred_source_type=rewrite_result.preferred_source_type,
                candidate_count=len(citations),
            ),
        )

    def _load_rows(self) -> list[dict]:
        if self._corpus_rows is None:
            self._corpus_rows = load_corpus_rows(self.corpus_path)
        return self._corpus_rows

    def _build_retriever(self, retriever_type: str, rows: list[dict], *, alpha: float):
        if retriever_type == "sparse":
            return SparseRetriever(rows)
        if retriever_type == "dense":
            return DenseRetriever(rows, index_dir=self.embedding_index_dir)
        if retriever_type == "hybrid":
            sparse = SparseRetriever(rows)
            dense = DenseRetriever(rows, index_dir=self.embedding_index_dir)
            return HybridRetriever(sparse, dense, alpha=alpha)
        raise ValueError(f"Unsupported RAG retriever: {retriever_type}")


def _citation_from_result(result: dict) -> RagCitation:
    return RagCitation(
        chunk_id=str(result["chunk_id"]),
        title=str(result.get("title") or ""),
        source_type=result["source_type"],
        url=str(result.get("url") or ""),
        score=float(result.get("score", 0.0)),
        text_excerpt=_excerpt(str(result.get("text") or ""), max_chars=500),
    )


def _build_extractive_answer(results: list[dict]) -> str:
    if not results:
        return "I could not find enough grounded context in the local corpus."

    sentences: list[str] = []
    for result in results:
        for sentence in _candidate_sentences(str(result.get("text") or "")):
            if len(sentence) < 30:
                continue
            sentences.append(sentence)
            break
        if len(sentences) >= 3:
            break

    if not sentences:
        return "I could not find enough grounded context in the local corpus."
    cited_ids = ", ".join(str(result["chunk_id"]) for result in results)
    return (
        "Based on retrieved local corpus chunks "
        f"({cited_ids}): "
        + " ".join(sentences)
    )


def _candidate_sentences(text: str) -> list[str]:
    without_code = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    without_labels = re.sub(r"\b(Document|Issue|Problem|Section path):\s*", " ", without_code)
    fragments: list[str] = []
    for raw_line in without_labels.splitlines():
        line = " ".join(raw_line.split()).strip(" -")
        if not line or line.startswith("**") or len(line) < 20:
            continue
        fragments.extend(SENTENCE_RE.split(line))

    cleaned: list[str] = []
    for fragment in fragments:
        sentence = fragment.strip()
        if not sentence or _looks_like_code_or_metadata(sentence):
            continue
        if len(sentence) > 260:
            sentence = sentence[:257].rstrip() + "..."
        cleaned.append(sentence)
    return cleaned


def _looks_like_code_or_metadata(sentence: str) -> bool:
    lowered = sentence.lower()
    if lowered.startswith(("version:", "platform:", "subsystem:", "```")):
        return True
    code_markers = ("const ", "var ", "function ", "require(", "=>", "{", "}")
    return sum(marker in sentence for marker in code_markers) >= 2


def _excerpt(text: str, *, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."
