#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.golden import (  # noqa: E402
    build_rag_golden_review_markdown,
    load_jsonl,
    write_text,
)


def main() -> int:
    corpus_path = ROOT / "data/rag/processed/rag_corpus.jsonl"
    candidates_path = ROOT / "data/rag/golden/rag_golden_candidates.jsonl"
    report_path = ROOT / "reports/rag_golden_review.md"

    corpus_rows = load_jsonl(corpus_path)
    candidate_rows = load_jsonl(candidates_path)
    report = build_rag_golden_review_markdown(candidate_rows=candidate_rows, corpus_rows=corpus_rows)
    write_text(report_path, report)
    print(f"Review report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
