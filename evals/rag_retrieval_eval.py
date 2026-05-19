#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.eval import run_rag_retrieval_eval  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate sparse RAG retrieval against the reviewed golden set.")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--report-path", default="reports/rag_eval_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code, result = run_rag_retrieval_eval(
        corpus_path=(ROOT / args.corpus_path).resolve(),
        golden_path=(ROOT / args.golden_path).resolve(),
        thresholds_path=(ROOT / args.thresholds_path).resolve(),
        report_path=(ROOT / args.report_path).resolve(),
    )
    if exit_code != 0 and not result.get("metrics"):
        print(result["message"])
        return exit_code

    print("RAG retrieval eval")
    print(f"Examples: {result['metrics']['example_count']}")
    print(f"hit@5: {result['metrics']['hit_at_5']:.4f}")
    print(f"hit@10: {result['metrics']['hit_at_10']:.4f}")
    print(f"MRR@10: {result['metrics']['mrr_at_10']:.4f}")
    print(f"Mean top score: {result['metrics']['mean_top_score']:.4f}")
    if result["passed"]:
        print("Threshold gate: PASS")
    else:
        print("Threshold gate: FAIL")
        for failure in result["failures"]:
            print(f"- {failure}")
    print(f"Report: {args.report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
