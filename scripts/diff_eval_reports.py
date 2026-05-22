"""Diff freshly generated eval reports against the previous green baseline.

The committed copies of the eval reports represent the last green build. CI saves
those committed copies to a baseline directory before re-running the evals (which
overwrite the working copies), then runs this script to flag any metric that
regressed below the baseline beyond a small tolerance.

This is a secondary regression signal layered on top of the absolute threshold
gates in eval_thresholds.yaml: a push can still be above the committed floor yet
worse than the last green build, and this catches that.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# (report filename, dotted metric path, human label). All tracked metrics are
# "higher is better", so a drop beyond TOLERANCE is a regression.
TRACKED: list[tuple[str, str, str]] = [
    ("classification_golden_eval_all.json", "models.selected_transformer.metrics.macro_f1", "classification macro-F1"),
    ("classification_golden_eval_all.json", "models.selected_transformer.metrics.accuracy", "classification accuracy"),
    ("rag_eval_hybrid_rewrite_boost_ci.json", "metrics.hit_at_5", "RAG hit@5"),
    ("rag_eval_hybrid_rewrite_boost_ci.json", "metrics.mrr_at_10", "RAG MRR@10"),
    ("rag_generation_eval_report.json", "answer_relevancy_avg", "RAG answer relevancy"),
    ("rag_generation_eval_report.json", "faithfulness_avg", "RAG faithfulness"),
    ("rag_generation_eval_report.json", "citation_coverage", "RAG citation coverage"),
    ("rag_generation_eval_report.json", "groundedness_pass_rate", "RAG groundedness pass rate"),
]

TOLERANCE = 0.01


def _read_metric(path: Path, dotted: str) -> float | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    node: object = data
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return float(node) if isinstance(node, (int, float)) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", required=True, help="Directory holding the previous green reports.")
    parser.add_argument("--current-dir", default="reports", help="Directory holding the freshly generated reports.")
    parser.add_argument("--tolerance", type=float, default=TOLERANCE)
    args = parser.parse_args()

    baseline_dir = Path(args.baseline_dir)
    current_dir = Path(args.current_dir)

    rows: list[tuple[str, str, str, str]] = []
    regressions: list[str] = []

    for filename, dotted, label in TRACKED:
        baseline = _read_metric(baseline_dir / filename, dotted)
        current = _read_metric(current_dir / filename, dotted)

        if current is None:
            rows.append((label, _fmt(baseline), "n/a", "current metric missing"))
            continue
        if baseline is None:
            rows.append((label, "n/a", _fmt(current), "no baseline (skipped)"))
            continue

        delta = current - baseline
        status = "ok"
        if delta < -args.tolerance:
            status = "REGRESSION"
            regressions.append(f"{label}: {baseline:.4f} -> {current:.4f} ({delta:+.4f})")
        rows.append((label, _fmt(baseline), _fmt(current), f"{delta:+.4f} {status}"))

    _print_table(rows)

    if regressions:
        print(f"\nFAILED: {len(regressions)} metric(s) regressed vs the previous green build (tolerance {args.tolerance}):")
        for line in regressions:
            print(f"  - {line}")
        return 1

    print("\nOK: no metric regressed beyond tolerance vs the previous green build.")
    return 0


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _print_table(rows: list[tuple[str, str, str, str]]) -> None:
    header = ("Metric", "Baseline", "Current", "Delta / status")
    widths = [max(len(str(r[i])) for r in (*rows, header)) for i in range(4)]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(header))
    print(line)
    print("  ".join("-" * widths[i] for i in range(4)))
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(4)))


if __name__ == "__main__":
    sys.exit(main())
