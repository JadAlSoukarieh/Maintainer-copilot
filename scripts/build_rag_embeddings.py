#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.golden import load_jsonl  # noqa: E402


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local dense embeddings for the RAG corpus.")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--output-dir", default="artifacts/rag/embeddings")
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_path = (ROOT / args.corpus_path).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "embedding_manifest.json"
    index_path = output_dir / "dense_index.npz"
    chunk_ids_path = output_dir / "chunk_ids.json"

    corpus_sha = sha256_file(corpus_path)
    rows = load_jsonl(corpus_path)
    if args.limit is not None:
        rows = rows[: args.limit]

    if not args.force and manifest_matches(
        manifest_path=manifest_path,
        index_path=index_path,
        chunk_ids_path=chunk_ids_path,
        embedding_model=args.embedding_model,
        corpus_path=corpus_path,
        corpus_sha256=corpus_sha,
        corpus_size=len(rows),
        limit=args.limit,
    ):
        print(f"Dense embedding index is already current: {output_dir}")
        return 0

    model = load_sentence_transformer(args.embedding_model)
    texts = [str(row["text"]) for row in rows]
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    ).astype(np.float32)

    np.savez_compressed(index_path, embeddings=embeddings)
    chunk_ids_path.write_text(json.dumps([row["chunk_id"] for row in rows], indent=2), encoding="utf-8")
    manifest = {
        "embedding_model": args.embedding_model,
        "corpus_path": str(corpus_path),
        "corpus_sha256": corpus_sha,
        "corpus_size": len(rows),
        "embedding_dim": int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "text_field_used": "text",
        "limit": args.limit,
        "normalized": True,
        "index_file": "dense_index.npz",
        "chunk_ids_file": "chunk_ids.json",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Built dense embedding index: {output_dir}")
    print(f"Corpus rows embedded: {len(rows)}")
    print(f"Embedding dim: {manifest['embedding_dim']}")
    return 0


def manifest_matches(
    *,
    manifest_path: Path,
    index_path: Path,
    chunk_ids_path: Path,
    embedding_model: str,
    corpus_path: Path,
    corpus_sha256: str,
    corpus_size: int,
    limit: int | None,
) -> bool:
    if not manifest_path.exists() or not index_path.exists() or not chunk_ids_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        manifest.get("embedding_model") == embedding_model
        and manifest.get("corpus_path") == str(corpus_path)
        and manifest.get("corpus_sha256") == corpus_sha256
        and manifest.get("corpus_size") == corpus_size
        and manifest.get("limit") == limit
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit(
            "sentence-transformers is required. Run python scripts/bootstrap_dev.py "
            "or install services/api with its dependencies."
        ) from exc
    return SentenceTransformer(model_name, local_files_only=True)


if __name__ == "__main__":
    raise SystemExit(main())
