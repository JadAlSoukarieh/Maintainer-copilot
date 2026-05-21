#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a human-friendly markdown review sheet for RAG generation labels.")
    parser.add_argument("--labels-path", default="data/rag/golden/rag_generation_human_labels.jsonl")
    parser.add_argument("--report-path", default="reports/rag_generation_eval_report.json")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--output-path", default="reports/rag_generation_human_review.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    labels = {row["golden_id"]: row for row in load_jsonl(ROOT / args.labels_path)}
    golden = {row["golden_id"]: row for row in load_jsonl(ROOT / args.golden_path)}
    eval_report = json.loads((ROOT / args.report_path).read_text(encoding="utf-8"))
    details = {row["golden_id"]: row for row in eval_report.get("details", []) if isinstance(row, dict) and row.get("golden_id")}

    markdown = build_review_markdown(labels=labels, golden=golden, details=details, report_path=args.report_path)
    output_path = ROOT / args.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote review helper: {args.output_path}")
    return 0


def build_review_markdown(
    *,
    labels: dict[str, dict[str, Any]],
    golden: dict[str, dict[str, Any]],
    details: dict[str, dict[str, Any]],
    report_path: str,
) -> str:
    lines: list[str] = []
    lines.append("# RAG Generation Human Review")
    lines.append("")
    lines.append("This report is a review helper for the five manually spot-checkable generation examples.")
    lines.append("It does not change labels automatically.")
    lines.append("")
    lines.append("## Manual steps")
    lines.append("")
    lines.append("1. Read each example below.")
    lines.append("2. Edit `data/rag/golden/rag_generation_human_labels.jsonl` directly.")
    lines.append("3. Update these fields when you have actually reviewed the row:")
    lines.append("   - `human_faithful`")
    lines.append("   - `human_relevant`")
    lines.append("   - `review_status`")
    lines.append("   - `human_notes`")
    lines.append("4. Only change `review_status` to `human_spot_checked` after a real manual review.")
    lines.append("5. Re-run `python evals/rag_generation_eval.py` after editing labels.")
    lines.append("")
    lines.append(f"Eval source: `{report_path}`")
    lines.append("")

    for golden_id, label in sorted(labels.items()):
        golden_row = golden.get(golden_id, {})
        detail = details.get(golden_id, {})
        lines.append(f"## {golden_id}")
        lines.append("")
        lines.append(f"**Question**  ")
        lines.append(f"{golden_row.get('question', '(missing question)')}")
        lines.append("")
        lines.append(f"**Ideal answer**  ")
        lines.append(f"{golden_row.get('ideal_answer', detail.get('ideal_answer', '(missing ideal answer)'))}")
        lines.append("")
        lines.append("**Generated answer**  ")
        lines.append(f"{detail.get('generated_answer', detail.get('answer', '(missing generated answer)'))}")
        lines.append("")
        lines.append("**Retrieved citations**")
        lines.append("")
        citations = detail.get("citations") or []
        if citations:
            for citation in citations:
                lines.append(f"- `{citation.get('title', '(untitled)')}`")
                lines.append(f"  - source_type: `{citation.get('source_type', '')}`")
                lines.append(f"  - chunk_id: `{citation.get('chunk_id', '')}`")
                lines.append(f"  - excerpt: {citation.get('text_excerpt', '')}")
        else:
            lines.append("- No citations recorded in the eval report.")
        lines.append("")
        lines.append("**Frozen judge result**")
        lines.append("")
        lines.append(f"- answer_relevancy: `{float(detail.get('answer_relevancy', 0.0)):.4f}`")
        lines.append(f"- faithfulness: `{float(detail.get('faithfulness', 0.0)):.4f}`")
        lines.append(f"- citation_coverage: `{bool(detail.get('citation_coverage', False))}`")
        lines.append(f"- groundedness_pass: `{bool(detail.get('groundedness_pass', False))}`")
        lines.append("")
        lines.append("**Current label fields**")
        lines.append("")
        lines.append(f"- human_faithful: `{label.get('human_faithful')}`")
        lines.append(f"- human_relevant: `{label.get('human_relevant')}`")
        lines.append(f"- review_status: `{label.get('review_status')}`")
        lines.append(f"- human_notes: {label.get('human_notes', '')}")
        lines.append("")
        lines.append("**Checklist**")
        lines.append("")
        lines.append("- [ ] Does the answer address the question?")
        lines.append("- [ ] Is the answer supported by the citations?")
        lines.append("- [ ] Does it avoid unsupported fixes or claims?")
        lines.append("- [ ] Are the citations useful?")
        lines.append("- [ ] Should this be marked `human_spot_checked`?")
        lines.append("")
    return "\n".join(lines) + "\n"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
