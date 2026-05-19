from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from maintcopilot_api.services.rag.golden import load_jsonl, validate_rag_golden
from maintcopilot_api.services.rag.query_transform import rewrite_query
from maintcopilot_api.services.rag.retrieval import (
    CrossEncoderReranker,
    DenseRetriever,
    HybridRetriever,
    RerankedRetriever,
    SparseRetriever,
    apply_metadata_boost,
    filter_corpus_rows,
)


def load_rag_thresholds(path: Path) -> dict[str, float]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = payload.get("rag_retrieval")
    if not isinstance(section, dict):
        raise ValueError("Threshold file is missing a rag_retrieval section.")
    return {
        "min_hit_at_5": float(section.get("min_hit_at_5", 0.0)),
        "min_mrr_at_10": float(section.get("min_mrr_at_10", 0.0)),
    }


def compute_retrieval_metrics(
    golden_rows: list[dict[str, Any]],
    corpus_rows: list[dict[str, Any]],
    *,
    top_k: int = 10,
    retriever: Any | None = None,
    query_rewrite_enabled: bool = False,
    metadata_boost_enabled: bool = False,
    metadata_boost_amount: float = 0.08,
) -> dict[str, Any]:
    active_retriever = retriever or SparseRetriever(corpus_rows)
    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks: list[float] = []
    top_scores: list[float] = []
    per_source_examples: Counter[str] = Counter()
    per_source_hits_at_5: Counter[str] = Counter()
    per_source_mrr: defaultdict[str, list[float]] = defaultdict(list)
    details: list[dict[str, Any]] = []

    for row in golden_rows:
        source_type = str(row.get("source_type", "unknown"))
        per_source_examples[source_type] += 1
        rewrite_result = rewrite_query(str(row["question"]))
        query_text = rewrite_result.rewritten_query if query_rewrite_enabled else str(row["question"])
        results = active_retriever.query(query_text, top_k=top_k)
        if metadata_boost_enabled:
            results = apply_metadata_boost(results, rewrite_result, boost_amount=metadata_boost_amount)[:top_k]
        top_scores.append(results[0]["score"] if results else 0.0)
        ground_truth_ids = set(row["ground_truth_chunk_ids"])

        rank = 0
        hit_at_5 = False
        hit_at_10 = False
        for index, result in enumerate(results, start=1):
            if result["chunk_id"] in ground_truth_ids:
                rank = index
                hit_at_10 = True
                if index <= 5:
                    hit_at_5 = True
                break

        if hit_at_5:
            hits_at_5 += 1
            per_source_hits_at_5[source_type] += 1
        if hit_at_10:
            hits_at_10 += 1
        reciprocal_rank = 1.0 / rank if rank else 0.0
        reciprocal_ranks.append(reciprocal_rank)
        per_source_mrr[source_type].append(reciprocal_rank)

        details.append(
            {
                "golden_id": row["golden_id"],
                "question": row["question"],
                "query_text": query_text,
                "intent": rewrite_result.intent,
                "source_type": source_type,
                "ground_truth_chunk_ids": row["ground_truth_chunk_ids"],
                "hit_at_5": hit_at_5,
                "hit_at_10": hit_at_10,
                "rank": rank or None,
                "top_results": [
                    {
                        "chunk_id": item["chunk_id"],
                        "score": item["score"],
                        "source_type": item["source_type"],
                    }
                    for item in results
                ],
            }
        )

    total = len(golden_rows)
    if total == 0:
        raise ValueError("At least one reviewed RAG golden example is required.")

    per_source_breakdown = {}
    for source_type, count in per_source_examples.items():
        per_source_breakdown[source_type] = {
            "count": count,
            "hit_at_5": per_source_hits_at_5[source_type] / count,
            "mrr_at_10": sum(per_source_mrr[source_type]) / count if count else 0.0,
        }

    return {
        "example_count": total,
        "hit_at_5": hits_at_5 / total,
        "hit_at_10": hits_at_10 / total,
        "mrr_at_10": sum(reciprocal_ranks) / total,
        "mean_top_score": sum(top_scores) / total,
        "per_source_breakdown": per_source_breakdown,
        "details": details,
    }


def evaluate_retrieval_thresholds(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    failures: list[str] = []
    if metrics["hit_at_5"] < thresholds["min_hit_at_5"]:
        failures.append(f"hit@5 {metrics['hit_at_5']:.4f} < {thresholds['min_hit_at_5']:.4f}")
    if metrics["mrr_at_10"] < thresholds["min_mrr_at_10"]:
        failures.append(f"MRR@10 {metrics['mrr_at_10']:.4f} < {thresholds['min_mrr_at_10']:.4f}")
    return failures


def run_rag_retrieval_eval(
    *,
    corpus_path: Path,
    golden_path: Path,
    thresholds_path: Path,
    report_path: Path,
    retriever_type: str = "sparse",
    embedding_index_dir: Path | None = None,
    alpha: float = 0.5,
    base_retriever_type: str = "hybrid",
    rerank_top_n: int = 20,
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    reranker: CrossEncoderReranker | None = None,
    query_rewrite_enabled: bool = False,
    metadata_boost_enabled: bool = False,
    metadata_boost_amount: float = 0.08,
    source_type: str | None = None,
) -> tuple[int, dict[str, Any]]:
    if not golden_path.exists():
        return 1, {
            "ok": False,
            "message": (
                "Final RAG golden set is missing.\n"
                "1. Run python scripts/make_rag_golden_candidates.py\n"
                "2. Run python scripts/review_rag_golden_candidates.py\n"
                "3. Manually create/edit data/rag/golden/rag_golden.jsonl from the draft\n"
                "4. Set needs_human_review=false on every final row\n"
                "5. Run python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final\n"
                "6. Rerun python evals/rag_retrieval_eval.py"
            ),
        }

    corpus_rows = load_jsonl(corpus_path)
    golden_rows = load_jsonl(golden_path)
    validation = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows, require_final=True)
    if not validation["ok"]:
        return 1, {
            "ok": False,
            "message": "Final RAG golden set failed validation. Run scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final and fix the reported rows first.",
            "validation": validation,
        }
    thresholds = load_rag_thresholds(thresholds_path)
    retrieval_corpus_rows = filter_corpus_rows(corpus_rows, source_type)
    retriever = build_retriever(
        retriever_type=retriever_type,
        corpus_rows=retrieval_corpus_rows,
        embedding_index_dir=embedding_index_dir,
        alpha=alpha,
        base_retriever_type=base_retriever_type,
        rerank_top_n=rerank_top_n,
        reranker_model=reranker_model,
        reranker=reranker,
    )
    try:
        metrics = compute_retrieval_metrics(
            golden_rows,
            retrieval_corpus_rows,
            retriever=retriever,
            query_rewrite_enabled=query_rewrite_enabled,
            metadata_boost_enabled=metadata_boost_enabled,
            metadata_boost_amount=metadata_boost_amount,
        )
    except RuntimeError as exc:
        return 1, {
            "ok": False,
            "retriever": retriever_type,
            "alpha": alpha if retriever_type in {"hybrid", "reranked"} else None,
            "base_retriever": base_retriever_type if retriever_type == "reranked" else None,
            "rerank_top_n": rerank_top_n if retriever_type == "reranked" else None,
            "reranker_model": reranker_model if retriever_type == "reranked" else None,
            "query_rewrite_enabled": query_rewrite_enabled,
            "metadata_boost_enabled": metadata_boost_enabled,
            "metadata_boost_amount": metadata_boost_amount,
            "source_type": source_type,
            "message": str(exc),
        }
    failures = evaluate_retrieval_thresholds(metrics, thresholds)

    report = {
        "retriever": retriever_type,
        "alpha": alpha if retriever_type in {"hybrid", "reranked"} else None,
        "base_retriever": base_retriever_type if retriever_type == "reranked" else None,
        "rerank_top_n": rerank_top_n if retriever_type == "reranked" else None,
        "reranker_model": reranker_model if retriever_type == "reranked" else None,
        "query_rewrite_enabled": query_rewrite_enabled,
        "metadata_boost_enabled": metadata_boost_enabled,
        "metadata_boost_amount": metadata_boost_amount,
        "source_type": source_type,
        "golden_path": str(golden_path),
        "corpus_path": str(corpus_path),
        "embedding_index_dir": str(embedding_index_dir) if embedding_index_dir is not None else None,
        "thresholds": thresholds,
        "metrics": metrics,
        "passed": not failures,
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return (0 if not failures else 1), report


def build_retriever(
    *,
    retriever_type: str,
    corpus_rows: list[dict[str, Any]],
    embedding_index_dir: Path | None,
    alpha: float,
    base_retriever_type: str,
    rerank_top_n: int,
    reranker_model: str,
    reranker: CrossEncoderReranker | None,
) -> Any:
    if retriever_type == "sparse":
        return SparseRetriever(corpus_rows)
    if retriever_type == "dense":
        if embedding_index_dir is None:
            raise ValueError("embedding_index_dir is required for dense retrieval.")
        return DenseRetriever(corpus_rows, index_dir=embedding_index_dir)
    if retriever_type == "hybrid":
        return _build_hybrid_retriever(corpus_rows=corpus_rows, embedding_index_dir=embedding_index_dir, alpha=alpha)
    if retriever_type == "reranked":
        base = _build_base_retriever_for_rerank(
            base_retriever_type=base_retriever_type,
            corpus_rows=corpus_rows,
            embedding_index_dir=embedding_index_dir,
            alpha=alpha,
        )
        active_reranker = reranker or CrossEncoderReranker(model_name=reranker_model)
        return RerankedRetriever(base, active_reranker, rerank_top_n=rerank_top_n)
    raise ValueError(f"Unsupported retriever type: {retriever_type}")


def _build_base_retriever_for_rerank(
    *,
    base_retriever_type: str,
    corpus_rows: list[dict[str, Any]],
    embedding_index_dir: Path | None,
    alpha: float,
) -> Any:
    if base_retriever_type == "sparse":
        return SparseRetriever(corpus_rows)
    if base_retriever_type == "dense":
        if embedding_index_dir is None:
            raise ValueError("embedding_index_dir is required for dense retrieval.")
        return DenseRetriever(corpus_rows, index_dir=embedding_index_dir)
    if base_retriever_type == "hybrid":
        return _build_hybrid_retriever(corpus_rows=corpus_rows, embedding_index_dir=embedding_index_dir, alpha=alpha)
    raise ValueError(f"Unsupported base retriever for reranking: {base_retriever_type}")


def _build_hybrid_retriever(
    *,
    corpus_rows: list[dict[str, Any]],
    embedding_index_dir: Path | None,
    alpha: float,
) -> HybridRetriever:
    if embedding_index_dir is None:
        raise ValueError("embedding_index_dir is required for hybrid retrieval.")
    sparse = SparseRetriever(corpus_rows)
    dense = DenseRetriever(corpus_rows, index_dir=embedding_index_dir)
    return HybridRetriever(sparse, dense, alpha=alpha)
