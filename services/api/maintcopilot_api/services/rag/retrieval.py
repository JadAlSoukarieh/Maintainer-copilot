from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Callable

import numpy as np

from maintcopilot_api.domain.rag import QueryRewriteResult
from maintcopilot_api.services.rag.golden import load_jsonl


TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/-]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "do",
    "for",
    "how",
    "i",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "use",
}
BOOST_MODULES = ("http", "https", "fs", "dns", "stream", "crypto", "tls", "os", "path", "net", "buffer")
ISSUE_INTENTS = {"issue", "debug", "memory", "network"}
DOC_INTENTS = {"docs", "api"}


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text):
        normalized = _normalize_token(token)
        if normalized and normalized not in STOPWORDS:
            tokens.append(normalized)
    return tokens


class SparseRetriever:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self._doc_term_counts = [Counter(tokenize(row["text"])) for row in rows]
        self._idf = self._compute_idf(self._doc_term_counts)
        self._doc_norms = [self._norm(term_counts) for term_counts in self._doc_term_counts]

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        query_counts = Counter(tokenize(query_text))
        query_norm = self._norm(query_counts)
        if not query_counts or query_norm == 0:
            return []

        results: list[dict] = []
        for row, term_counts, doc_norm in zip(self.rows, self._doc_term_counts, self._doc_norms, strict=True):
            if doc_norm == 0:
                continue
            score = self._score(query_counts, query_norm, term_counts, doc_norm)
            if score <= 0:
                continue
            results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "score": score,
                    "source_type": row["source_type"],
                    "title": row["title"],
                    "url": row["url"],
                    "text": row["text"],
                    "metadata": row["metadata"],
                }
            )

        return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]

    def _score(self, query_counts: Counter[str], query_norm: float, doc_counts: Counter[str], doc_norm: float) -> float:
        dot = 0.0
        for token, query_tf in query_counts.items():
            if token not in doc_counts:
                continue
            idf = self._idf.get(token, 0.0)
            dot += (query_tf * idf) * (doc_counts[token] * idf)
        return dot / (query_norm * doc_norm) if dot else 0.0

    def _norm(self, term_counts: Counter[str]) -> float:
        total = 0.0
        for token, tf in term_counts.items():
            idf = self._idf.get(token, 0.0)
            total += (tf * idf) ** 2
        return math.sqrt(total)

    @staticmethod
    def _compute_idf(doc_term_counts: list[Counter[str]]) -> dict[str, float]:
        doc_count = len(doc_term_counts)
        document_frequency: Counter[str] = Counter()
        for term_counts in doc_term_counts:
            for token in term_counts:
                document_frequency[token] += 1
        return {
            token: math.log((1 + doc_count) / (1 + frequency)) + 1.0
            for token, frequency in document_frequency.items()
        }


class DenseRetriever:
    def __init__(
        self,
        rows: list[dict],
        *,
        index_dir: Path,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        query_encoder: Callable[[list[str]], np.ndarray] | None = None,
    ) -> None:
        self.rows_by_id = {row["chunk_id"]: row for row in rows}
        self.index_dir = Path(index_dir)
        self.embedding_model = embedding_model
        self.query_encoder = query_encoder
        self._model = None
        self.chunk_ids = self._load_chunk_ids(self.index_dir / "chunk_ids.json")
        self.embeddings = self._load_embeddings(self.index_dir / "dense_index.npz")
        if len(self.chunk_ids) != self.embeddings.shape[0]:
            raise ValueError("Dense index chunk id count does not match embedding row count.")

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        if not query_text.strip():
            return []
        query_embedding = self._encode_query(query_text)
        scores = self.embeddings @ query_embedding
        if scores.size == 0:
            return []
        results: list[dict] = []
        for index in np.argsort(scores)[::-1]:
            chunk_id = self.chunk_ids[int(index)]
            row = self.rows_by_id.get(chunk_id)
            if row is None:
                continue
            results.append(_result_from_row(row, float(scores[int(index)])))
            if len(results) >= top_k:
                break
        return results

    def _encode_query(self, query_text: str) -> np.ndarray:
        if self.query_encoder is not None:
            encoded = self.query_encoder([query_text])
        else:
            if self._model is None:
                self._model = _load_sentence_transformer(self.embedding_model)
            encoded = self._model.encode([query_text], normalize_embeddings=True, convert_to_numpy=True)
        array = np.asarray(encoded, dtype=np.float32)
        if array.ndim == 2:
            array = array[0]
        norm = np.linalg.norm(array)
        if norm == 0:
            return array
        return array / norm

    @staticmethod
    def _load_chunk_ids(path: Path) -> list[str]:
        import json

        if not path.exists():
            raise FileNotFoundError(f"Dense retrieval chunk id file is missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
            raise ValueError("Dense retrieval chunk_ids.json must contain a JSON list of strings.")
        return payload

    @staticmethod
    def _load_embeddings(path: Path) -> np.ndarray:
        if not path.exists():
            raise FileNotFoundError(f"Dense retrieval index file is missing: {path}")
        payload = np.load(path)
        embeddings = np.asarray(payload["embeddings"], dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("Dense retrieval embeddings must be a 2D array.")
        return embeddings


class HybridRetriever:
    def __init__(
        self,
        sparse_retriever: SparseRetriever,
        dense_retriever: DenseRetriever,
        *,
        alpha: float = 0.5,
    ) -> None:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Hybrid alpha must be between 0.0 and 1.0.")
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever
        self.alpha = alpha

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        if self.alpha == 1.0:
            return self.sparse_retriever.query(query_text, top_k=top_k)
        if self.alpha == 0.0:
            return self.dense_retriever.query(query_text, top_k=top_k)

        fetch_k = max(top_k * 5, 25)
        sparse_results = self.sparse_retriever.query(query_text, top_k=fetch_k)
        dense_results = self.dense_retriever.query(query_text, top_k=fetch_k)
        sparse_scores = _scores_by_chunk_id(sparse_results)
        dense_scores = _scores_by_chunk_id(dense_results)
        normalized_sparse = _normalize_scores(sparse_scores)
        normalized_dense = _normalize_scores(dense_scores)
        results_by_id = {item["chunk_id"]: item for item in sparse_results + dense_results}

        combined: list[dict] = []
        for chunk_id, result in results_by_id.items():
            sparse_score = normalized_sparse.get(chunk_id, 0.0)
            dense_score = normalized_dense.get(chunk_id, 0.0)
            score = self.alpha * sparse_score + (1.0 - self.alpha) * dense_score
            item = dict(result)
            item["score"] = score
            item["sparse_score"] = sparse_scores.get(chunk_id, 0.0)
            item["dense_score"] = dense_scores.get(chunk_id, 0.0)
            combined.append(item)

        return sorted(combined, key=lambda item: item["score"], reverse=True)[:top_k]


class CrossEncoderReranker:
    def __init__(
        self,
        *,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        scorer: Callable[[list[tuple[str, str]]], np.ndarray | list[float]] | None = None,
    ) -> None:
        self.model_name = model_name
        self.scorer = scorer
        self._model = None

    def score(self, query_text: str, candidates: list[dict]) -> list[float]:
        if not candidates:
            return []
        pairs = [(query_text, str(candidate["text"])) for candidate in candidates]
        if self.scorer is not None:
            raw_scores = self.scorer(pairs)
        else:
            if self._model is None:
                self._model = _load_cross_encoder(self.model_name)
            raw_scores = self._model.predict(pairs)
        scores = np.asarray(raw_scores, dtype=np.float32).reshape(-1)
        if scores.shape[0] != len(candidates):
            raise ValueError("Reranker returned a score count that does not match candidate count.")
        return [float(score) for score in scores]


class RerankedRetriever:
    def __init__(
        self,
        base_retriever: SparseRetriever | DenseRetriever | HybridRetriever,
        reranker: CrossEncoderReranker,
        *,
        rerank_top_n: int = 20,
    ) -> None:
        if rerank_top_n <= 0:
            raise ValueError("rerank_top_n must be greater than zero.")
        self.base_retriever = base_retriever
        self.reranker = reranker
        self.rerank_top_n = rerank_top_n

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        candidates = self.base_retriever.query(query_text, top_k=max(top_k, self.rerank_top_n))
        if not candidates:
            return []

        reranker_scores = self.reranker.score(query_text, candidates)
        reranked: list[dict] = []
        for rank, (candidate, reranker_score) in enumerate(
            sorted(
                zip(candidates, reranker_scores, strict=True),
                key=lambda item: item[1],
                reverse=True,
            ),
            start=1,
        ):
            item = dict(candidate)
            item["original_score"] = float(candidate.get("score", 0.0))
            item["reranker_score"] = float(reranker_score)
            item["final_rank"] = rank
            item["score"] = float(reranker_score)
            reranked.append(item)
        return reranked[:top_k]


def load_corpus_rows(path: Path) -> list[dict]:
    return load_jsonl(path)


def filter_corpus_rows(rows: list[dict], source_type: str | None = None) -> list[dict]:
    if source_type is None:
        return list(rows)
    if source_type not in {"doc", "resolved_issue", "issue_comment"}:
        raise ValueError("source_type must be doc, resolved_issue, issue_comment, or None.")
    return [row for row in rows if row.get("source_type") == source_type]


def apply_metadata_boost(
    results: list[dict],
    rewrite_result: QueryRewriteResult,
    *,
    boost_amount: float = 0.08,
) -> list[dict]:
    boosted: list[dict] = []
    query_terms = _metadata_query_terms(rewrite_result)
    for result in results:
        original_score = float(result.get("score", 0.0))
        metadata_boost = _metadata_boost_for_result(result, rewrite_result, query_terms, boost_amount)
        item = dict(result)
        item["original_score"] = original_score
        item["metadata_boost"] = metadata_boost
        item["final_score"] = original_score + metadata_boost
        item["score"] = item["final_score"]
        boosted.append(item)
    return sorted(boosted, key=lambda item: item["final_score"], reverse=True)


def _result_from_row(row: dict, score: float) -> dict:
    return {
        "chunk_id": row["chunk_id"],
        "score": score,
        "source_type": row["source_type"],
        "title": row["title"],
        "url": row["url"],
        "text": row["text"],
        "metadata": row["metadata"],
    }


def _metadata_boost_for_result(
    result: dict,
    rewrite_result: QueryRewriteResult,
    query_terms: set[str],
    boost_amount: float,
) -> float:
    if boost_amount <= 0:
        return 0.0

    score_boost = 0.0
    source_type = result.get("source_type")
    if rewrite_result.preferred_source_type and source_type == rewrite_result.preferred_source_type:
        score_boost += boost_amount
    if rewrite_result.intent in DOC_INTENTS and source_type == "doc":
        score_boost += boost_amount
    if rewrite_result.intent in ISSUE_INTENTS and source_type in {"resolved_issue", "issue_comment"}:
        score_boost += boost_amount

    haystack = _metadata_haystack(result)
    if any(term in query_terms and term in haystack for term in BOOST_MODULES):
        score_boost += boost_amount
    return score_boost


def _metadata_query_terms(rewrite_result: QueryRewriteResult) -> set[str]:
    text = f"{rewrite_result.original_query} {rewrite_result.rewritten_query} {' '.join(rewrite_result.added_terms)}"
    return {tokenize_item for tokenize_item in tokenize(text)}


def _metadata_haystack(result: dict) -> str:
    metadata = result.get("metadata") or {}
    pieces = [
        str(result.get("title") or ""),
        str(metadata.get("path") or ""),
        str(metadata.get("section") or ""),
    ]
    return " ".join(pieces).lower()


def _scores_by_chunk_id(results: list[dict]) -> dict[str, float]:
    return {str(result["chunk_id"]): float(result["score"]) for result in results}


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    values = list(scores.values())
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return {chunk_id: 1.0 for chunk_id in scores}
    return {chunk_id: (score - minimum) / (maximum - minimum) for chunk_id, score in scores.items()}


def _load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for dense RAG retrieval. "
            "Run python scripts/bootstrap_dev.py or install the API package dependencies."
        ) from exc
    return SentenceTransformer(
        model_name,
        local_files_only=True,
        device="cpu",
        model_kwargs={"low_cpu_mem_usage": False},
    )


def _load_cross_encoder(model_name: str):
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for RAG reranking. "
            "Run python scripts/bootstrap_dev.py or install the API package dependencies."
        ) from exc
    try:
        return CrossEncoder(
            model_name,
            local_files_only=True,
            device="cpu",
            automodel_args={"low_cpu_mem_usage": False},
        )
    except OSError as exc:
        raise RuntimeError(
            "The reranker model is not cached locally: "
            f"{model_name}. Pre-download it into the local Hugging Face cache before "
            f"running reranked retrieval, for example with huggingface-cli download {model_name}."
        ) from exc


def _normalize_token(token: str) -> str:
    normalized = token.lower()
    if normalized.endswith("ing") and len(normalized) > 5:
        normalized = normalized[:-3]
    elif normalized.endswith("ed") and len(normalized) > 4:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized
