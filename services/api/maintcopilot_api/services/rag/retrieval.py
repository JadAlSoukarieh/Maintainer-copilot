from __future__ import annotations

import math
import re
from collections import Counter


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


def _normalize_token(token: str) -> str:
    normalized = token.lower()
    if normalized.endswith("ing") and len(normalized) > 5:
        normalized = normalized[:-3]
    elif normalized.endswith("ed") and len(normalized) > 4:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized
