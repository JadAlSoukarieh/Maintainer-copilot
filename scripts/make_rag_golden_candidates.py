#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.golden import (  # noqa: E402
    generate_rag_golden_candidates,
    load_jsonl,
    write_jsonl,
)


def main() -> int:
    corpus_path = ROOT / "data/rag/processed/rag_corpus.jsonl"
    output_path = ROOT / "data/rag/golden/rag_golden_candidates.jsonl"
    corpus_rows = load_jsonl(corpus_path)
    candidates = generate_rag_golden_candidates(corpus_rows)
    write_jsonl(output_path, candidates)

    distribution = Counter(row["source_type"] for row in candidates)
    print(f"Wrote {len(candidates)} candidate rows to {output_path}")
    print(f"Source distribution: {dict(distribution)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
