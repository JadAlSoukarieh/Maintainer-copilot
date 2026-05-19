#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.golden import load_jsonl, validate_rag_golden  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate RAG golden candidate or reviewed files.")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden_candidates.jsonl")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--require-final", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    golden_rows = load_jsonl(ROOT / args.golden_path)
    corpus_rows = load_jsonl(ROOT / args.corpus_path)
    result = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows, require_final=args.require_final)

    print(f"Rows: {result['count']}")
    print(f"Source distribution: {result['source_distribution']}")
    if result["ok"]:
        print("Validation: PASS")
        return 0
    print("Validation: FAIL")
    for error in result["errors"]:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
