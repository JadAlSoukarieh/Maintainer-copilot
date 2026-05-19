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
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval against the reviewed golden set.")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--report-path")
    parser.add_argument("--retriever", choices=["sparse", "dense", "hybrid", "reranked"], default="sparse")
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--embedding-index-dir", default="artifacts/rag/embeddings")
    parser.add_argument("--base-retriever", choices=["sparse", "dense", "hybrid"], default="hybrid")
    parser.add_argument("--rerank-top-n", type=int, default=20)
    parser.add_argument("--reranker-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    parser.add_argument("--query-rewrite", action="store_true")
    parser.add_argument("--metadata-boost", action="store_true")
    parser.add_argument("--metadata-boost-amount", type=float, default=0.08)
    parser.add_argument("--source-type", choices=["doc", "resolved_issue"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = args.report_path or f"reports/rag_eval_{args.retriever}.json"
    exit_code, result = run_rag_retrieval_eval(
        corpus_path=(ROOT / args.corpus_path).resolve(),
        golden_path=(ROOT / args.golden_path).resolve(),
        thresholds_path=(ROOT / args.thresholds_path).resolve(),
        report_path=(ROOT / report_path).resolve(),
        retriever_type=args.retriever,
        embedding_index_dir=(ROOT / args.embedding_index_dir).resolve(),
        alpha=args.alpha,
        base_retriever_type=args.base_retriever,
        rerank_top_n=args.rerank_top_n,
        reranker_model=args.reranker_model,
        query_rewrite_enabled=args.query_rewrite,
        metadata_boost_enabled=args.metadata_boost,
        metadata_boost_amount=args.metadata_boost_amount,
        source_type=args.source_type,
    )
    if exit_code != 0 and not result.get("metrics"):
        print(result["message"])
        return exit_code

    print("RAG retrieval eval")
    print(f"Retriever: {result['retriever']}")
    if result["retriever"] == "hybrid":
        print(f"Alpha: {result['alpha']:.2f}")
    if result["retriever"] == "reranked":
        print(f"Base retriever: {result['base_retriever']}")
        print(f"Alpha: {result['alpha']:.2f}")
        print(f"Rerank top_n: {result['rerank_top_n']}")
        print(f"Reranker model: {result['reranker_model']}")
    print(f"Query rewrite: {result['query_rewrite_enabled']}")
    print(f"Metadata boost: {result['metadata_boost_enabled']}")
    if result["metadata_boost_enabled"]:
        print(f"Metadata boost amount: {result['metadata_boost_amount']:.2f}")
    if result["source_type"]:
        print(f"Source type filter: {result['source_type']}")
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
    print(f"Report: {report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
