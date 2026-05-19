#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.eval import run_rag_retrieval_eval  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep sparse+dense RAG hybrid alpha values.")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--embedding-index-dir", default="artifacts/rag/embeddings")
    parser.add_argument("--output-path", default="artifacts/rag/hybrid_alpha_sweep.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
    results = []
    for alpha in alphas:
        report_path = ROOT / "reports" / f"rag_eval_hybrid_alpha_{str(alpha).replace('.', '_')}.json"
        exit_code, result = run_rag_retrieval_eval(
            corpus_path=(ROOT / args.corpus_path).resolve(),
            golden_path=(ROOT / args.golden_path).resolve(),
            thresholds_path=(ROOT / args.thresholds_path).resolve(),
            report_path=report_path.resolve(),
            retriever_type="hybrid",
            embedding_index_dir=(ROOT / args.embedding_index_dir).resolve(),
            alpha=alpha,
        )
        metrics = result["metrics"]
        per_source = metrics["per_source_breakdown"]
        results.append(
            {
                "alpha": alpha,
                "hit_at_5": metrics["hit_at_5"],
                "hit_at_10": metrics["hit_at_10"],
                "mrr_at_10": metrics["mrr_at_10"],
                "per_source_hit_at_5": {
                    source_type: source_metrics["hit_at_5"]
                    for source_type, source_metrics in per_source.items()
                },
                "passed": result["passed"],
                "failures": result["failures"],
                "report_path": str(report_path),
            }
        )
        print(
            f"alpha={alpha:.2f} hit@5={metrics['hit_at_5']:.4f} "
            f"hit@10={metrics['hit_at_10']:.4f} MRR@10={metrics['mrr_at_10']:.4f}"
        )
        if exit_code != 0:
            print(f"Threshold gate failed for alpha={alpha:.2f}: {result['failures']}")

    output_path = (ROOT / args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print(f"Wrote alpha sweep: {args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
