#!/usr/bin/env python3
"""Compare two dense embedding models on the RAG golden retrieval set.

Usage:
  python evals/embedding_comparison.py \
    --model-a sentence-transformers/all-MiniLM-L6-v2 \
    --model-b sentence-transformers/all-MiniLM-L12-v2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.eval import compute_retrieval_metrics  # noqa: E402
from maintcopilot_api.services.rag.golden import load_jsonl, validate_rag_golden  # noqa: E402
from maintcopilot_api.services.rag.retrieval import DenseRetriever  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model-a", default="sentence-transformers/all-MiniLM-L6-v2")
    p.add_argument("--model-b", default="sentence-transformers/all-MiniLM-L12-v2")
    p.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    p.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    p.add_argument("--existing-index-dir", default="artifacts/rag/embeddings",
                   help="Pre-built index dir for --model-a (skip rebuild if present)")
    p.add_argument("--output-dir", default="artifacts/rag/embeddings_compare",
                   help="Dir for --model-b index and comparison report")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--report-path", default="reports/embedding_comparison_report.json")
    return p.parse_args()


def load_or_build_index(
    model_name: str,
    corpus_rows: list[dict],
    index_dir: Path,
    *,
    batch_size: int,
) -> tuple[np.ndarray, list[str]]:
    """Load existing index or build a new one, returning (embeddings, chunk_ids)."""
    index_path = index_dir / "dense_index.npz"
    ids_path = index_dir / "chunk_ids.json"
    manifest_path = index_dir / "embedding_manifest.json"

    if index_path.exists() and ids_path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("embedding_model") == model_name and manifest.get("corpus_size") == len(corpus_rows):
            print(f"  Loaded existing index for {model_name} ({index_dir.name})")
            data = np.load(index_path)
            embeddings = data["embeddings"]
            chunk_ids = json.loads(ids_path.read_text())
            return embeddings, chunk_ids

    print(f"  Building index for {model_name} ({len(corpus_rows)} chunks)…")
    from sentence_transformers import SentenceTransformer
    t0 = time.perf_counter()
    model = SentenceTransformer(model_name, local_files_only=False)
    texts = [str(r["text"]) for r in corpus_rows]
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    ).astype(np.float32)
    elapsed = time.perf_counter() - t0
    print(f"  Done in {elapsed:.1f}s — dim={embeddings.shape[1]}")

    index_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(index_path, embeddings=embeddings)
    chunk_ids = [r["chunk_id"] for r in corpus_rows]
    ids_path.write_text(json.dumps(chunk_ids, indent=2))
    manifest_path.write_text(json.dumps({
        "embedding_model": model_name,
        "corpus_size": len(corpus_rows),
        "embedding_dim": int(embeddings.shape[1]),
        "normalized": True,
    }, indent=2))
    return embeddings, chunk_ids


def eval_model(
    model_name: str,
    corpus_rows: list[dict],
    golden_rows: list[dict],
    index_dir: Path,
    *,
    batch_size: int,
) -> dict:
    load_or_build_index(model_name, corpus_rows, index_dir, batch_size=batch_size)
    retriever = DenseRetriever(corpus_rows, index_dir=index_dir, embedding_model=model_name)
    return compute_retrieval_metrics(golden_rows, corpus_rows, top_k=10, retriever=retriever)


def main() -> int:
    args = parse_args()
    corpus_path = (ROOT / args.corpus_path).resolve()
    golden_path = (ROOT / args.golden_path).resolve()
    report_path = (ROOT / args.report_path).resolve()
    existing_index_dir = (ROOT / args.existing_index_dir).resolve()
    compare_index_dir = (ROOT / args.output_dir).resolve()

    corpus_rows = load_jsonl(corpus_path)
    golden_rows_raw = load_jsonl(golden_path)
    validation = validate_rag_golden(golden_rows=golden_rows_raw, corpus_rows=corpus_rows)
    if not validation.get("ok"):
        print("Golden set validation errors:", validation.get("errors"))
        return 1
    golden_rows = golden_rows_raw
    print(f"Corpus: {len(corpus_rows)} chunks  |  Golden: {len(golden_rows)} examples")

    print(f"\n[A] {args.model_a}")
    metrics_a = eval_model(args.model_a, corpus_rows, golden_rows, existing_index_dir, batch_size=args.batch_size)

    print(f"\n[B] {args.model_b}")
    model_b_dir = compare_index_dir / args.model_b.replace("/", "_")
    metrics_b = eval_model(args.model_b, corpus_rows, golden_rows, model_b_dir, batch_size=args.batch_size)

    def _fmt(m: dict) -> dict:
        return {
            "hit_at_5": round(m["hit_at_5"], 4),
            "hit_at_10": round(m["hit_at_10"], 4),
            "mrr_at_10": round(m["mrr_at_10"], 4),
        }

    report = {
        "models": {
            "a": {"name": args.model_a, **_fmt(metrics_a)},
            "b": {"name": args.model_b, **_fmt(metrics_b)},
        },
        "delta": {
            "hit_at_5": round(metrics_b["hit_at_5"] - metrics_a["hit_at_5"], 4),
            "hit_at_10": round(metrics_b["hit_at_10"] - metrics_a["hit_at_10"], 4),
            "mrr_at_10": round(metrics_b["mrr_at_10"] - metrics_a["mrr_at_10"], 4),
        },
        "winner": args.model_b if metrics_b["mrr_at_10"] > metrics_a["mrr_at_10"] else args.model_a,
        "corpus_size": len(corpus_rows),
        "golden_size": len(golden_rows),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))

    print("\n=== Embedding model comparison ===")
    print(f"{'Model':<50} {'hit@5':>6} {'hit@10':>7} {'MRR@10':>7}")
    print("-" * 74)
    for key in ("a", "b"):
        m = report["models"][key]
        print(f"{m['name']:<50} {m['hit_at_5']:>6.4f} {m['hit_at_10']:>7.4f} {m['mrr_at_10']:>7.4f}")
    delta = report["delta"]
    sign = lambda v: f"+{v:.4f}" if v >= 0 else f"{v:.4f}"
    print(f"{'Δ (B − A)':<50} {sign(delta['hit_at_5']):>6} {sign(delta['hit_at_10']):>7} {sign(delta['mrr_at_10']):>7}")
    print(f"\nWinner (MRR@10): {report['winner']}")
    print(f"Report saved → {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
