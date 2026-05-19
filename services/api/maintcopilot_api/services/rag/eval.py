from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from maintcopilot_api.services.rag.golden import load_jsonl
from maintcopilot_api.services.rag.retrieval import SparseRetriever


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
) -> dict[str, Any]:
    retriever = SparseRetriever(corpus_rows)
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
        results = retriever.query(str(row["question"]), top_k=top_k)
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
) -> tuple[int, dict[str, Any]]:
    if not golden_path.exists():
        return 1, {
            "ok": False,
            "message": (
                "Final RAG golden set is missing. Review data/rag/golden/rag_golden_candidates.jsonl, "
                "save the reviewed file as data/rag/golden/rag_golden.jsonl, set needs_human_review=false, "
                "then rerun validation and retrieval eval."
            ),
        }

    corpus_rows = load_jsonl(corpus_path)
    golden_rows = load_jsonl(golden_path)
    thresholds = load_rag_thresholds(thresholds_path)
    metrics = compute_retrieval_metrics(golden_rows, corpus_rows)
    failures = evaluate_retrieval_thresholds(metrics, thresholds)

    report = {
        "golden_path": str(golden_path),
        "corpus_path": str(corpus_path),
        "thresholds": thresholds,
        "metrics": metrics,
        "passed": not failures,
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return (0 if not failures else 1), report
