from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReportSummaryService:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def summary(self) -> dict[str, Any]:
        classical = self._read_json("artifacts/classifier/classical/metrics.json")
        transformer = self._read_json("artifacts/classifier/transformer/metrics.json")
        llm = self._read_json("artifacts/classifier/llm_baseline/metrics.json")
        comparison = self._read_json("artifacts/classifier/comparison/classification_report.json")
        classification_eval = self._read_json("reports/eval_report.json")
        classification_eval_all = self._read_json("reports/classification_golden_eval_all.json")
        rag_sparse = self._read_json("reports/rag_eval_sparse.json")
        rag_dense = self._read_json("reports/rag_eval_dense.json")
        rag_hybrid = self._read_json("reports/rag_eval_hybrid_rewrite_boost.json")
        rag_reranked = self._read_json("reports/rag_eval_reranked.json")
        rag_generation = self._read_json("reports/rag_generation_eval_report.json")

        return {
            "classifier": {
                "selected": _nested(comparison, "deployment_choice") or "transformer_roberta_base",
                "classical_macro_f1": _nested(classical, "test", "macro_f1") or classical.get("macro_f1"),
                "transformer_macro_f1": _nested(transformer, "test", "macro_f1") or transformer.get("macro_f1"),
                "llm_macro_f1": _nested(llm, "test", "macro_f1") or llm.get("macro_f1"),
            },
            "classification_golden": {
                "accuracy": _nested(classification_eval, "metrics", "accuracy"),
                "macro_f1": _nested(classification_eval, "metrics", "macro_f1"),
                "passed": classification_eval.get("passed"),
                "all_models": classification_eval_all.get("models", {}),
            },
            "rag_retrieval": {
                "selected": "reranked_hybrid_rewrite_boost",
                "sparse": _retrieval_metrics(rag_sparse),
                "dense": _retrieval_metrics(rag_dense),
                "hybrid_rewrite_boost": _retrieval_metrics(rag_hybrid),
                "reranked": _retrieval_metrics(rag_reranked),
            },
            "rag_generation": {
                "judge_version": rag_generation.get("judge_version"),
                "answer_relevancy_avg": rag_generation.get("answer_relevancy_avg"),
                "faithfulness_avg": rag_generation.get("faithfulness_avg"),
                "citation_coverage": rag_generation.get("citation_coverage"),
                "groundedness_pass_rate": rag_generation.get("groundedness_pass_rate"),
                "threshold_gate": rag_generation.get("threshold_gate"),
            },
            "notes": {
                "long_term_memory": "pgvector_episodic_with_text_fallback",
                "observability": "recent_events_request_ids_not_full_tracing",
            },
        }

    def _read_json(self, relative_path: str) -> dict[str, Any]:
        path = self.repo_root / relative_path
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _retrieval_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    return {
        "hit_at_5": metrics.get("hit_at_5"),
        "hit_at_10": metrics.get("hit_at_10"),
        "mrr_at_10": metrics.get("mrr_at_10"),
        "passed": payload.get("passed"),
    }
