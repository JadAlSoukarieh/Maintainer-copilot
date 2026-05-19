#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.golden import create_rag_golden_draft, load_jsonl, write_jsonl  # noqa: E402


def main() -> int:
    candidates_path = ROOT / "data/rag/golden/rag_golden_candidates.jsonl"
    draft_path = ROOT / "data/rag/golden/rag_golden.draft.jsonl"

    candidate_rows = load_jsonl(candidates_path)
    draft_rows = create_rag_golden_draft(candidate_rows)
    write_jsonl(draft_path, draft_rows)
    print(f"Draft written to {draft_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
