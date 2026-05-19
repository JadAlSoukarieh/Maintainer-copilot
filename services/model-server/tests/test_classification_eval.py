from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.classification_eval import compute_metrics, evaluate_thresholds, run_eval


def test_metric_computation() -> None:
    metrics = compute_metrics(
        ["bug", "feature", "docs", "question"],
        ["bug", "feature", "question", "question"],
    )
    assert metrics["accuracy"] == 0.75
    assert metrics["per_class_f1"]["bug"] == 1.0
    assert metrics["per_class_f1"]["docs"] == 0.0
    assert metrics["confusion_matrix"]["labels"] == ["bug", "feature", "docs", "question"]


def test_threshold_pass_fail_logic() -> None:
    metrics = {
        "accuracy": 0.7,
        "macro_f1": 0.6,
        "per_class_f1": {"bug": 0.4, "feature": 0.5, "docs": 0.6, "question": 0.7},
    }
    thresholds = {
        "min_accuracy": 0.6,
        "min_macro_f1": 0.55,
        "min_per_class_f1": {"bug": 0.3, "feature": 0.4, "docs": 0.5, "question": 0.5},
    }
    assert evaluate_thresholds(metrics, thresholds) == []
    failing = evaluate_thresholds(
        metrics,
        {
            "min_accuracy": 0.8,
            "min_macro_f1": 0.7,
            "min_per_class_f1": {"bug": 0.5, "feature": 0.4, "docs": 0.5, "question": 0.5},
        },
    )
    assert any("accuracy" in item for item in failing)
    assert any("macro_f1" in item for item in failing)
    assert any("bug f1" in item for item in failing)


def test_report_json_shape(tmp_path: Path) -> None:
    report_path = tmp_path / "eval_report.json"
    exit_code, report = run_eval(
        golden_path=ROOT / "data/golden/classification_golden.jsonl",
        thresholds_path=ROOT / "evals/eval_thresholds.yaml",
        report_path=report_path,
    )
    assert exit_code in {0, 1}
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["report_version"] == "classification-golden-v1"
    assert "metrics" in loaded
    assert "predictions" in loaded
    assert len(loaded["predictions"]) == 25
    assert loaded["metrics"]["confusion_matrix"]["labels"] == ["bug", "feature", "docs", "question"]
    assert loaded["passed"] == report["passed"]
