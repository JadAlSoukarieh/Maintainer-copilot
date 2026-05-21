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


def test_all_mode_report_shape(tmp_path: Path) -> None:
    report_path = tmp_path / "eval_all_report.json"
    exit_code, report = run_eval(
        golden_path=ROOT / "data/golden/classification_golden.jsonl",
        thresholds_path=ROOT / "evals/eval_thresholds.yaml",
        report_path=report_path,
        model="all",
    )

    assert exit_code in {0, 1}
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["report_version"] == "classification-golden-v2"
    assert "models" in loaded
    assert "selected_transformer" in loaded["models"]
    assert "classical" in loaded["models"]
    assert "llm_baseline_predictions" in loaded["models"]


def test_all_mode_primary_gate_allows_baseline_warning(tmp_path: Path) -> None:
    golden_path, thresholds_path = _write_tiny_eval_inputs(tmp_path)
    report_path = tmp_path / "eval_all_primary.json"
    exit_code, report = run_eval(
        golden_path=golden_path,
        thresholds_path=thresholds_path,
        report_path=report_path,
        model="all",
        gate="primary",
        evaluator_overrides={
            "selected_transformer": _fake_eval("bug"),
            "classical": _fake_eval("question"),
            "llm_baseline_predictions": _fake_eval("bug"),
        },
    )

    assert exit_code == 0
    assert report["blocking_failure"] is False
    assert report["models"]["selected_transformer"]["status"] == "PASS"
    assert report["models"]["classical"]["status"] == "WARN"
    assert "classical" in report["baseline_failures"]


def test_all_gate_blocks_baseline_failure(tmp_path: Path) -> None:
    golden_path, thresholds_path = _write_tiny_eval_inputs(tmp_path)
    report_path = tmp_path / "eval_all_strict.json"
    exit_code, report = run_eval(
        golden_path=golden_path,
        thresholds_path=thresholds_path,
        report_path=report_path,
        model="all",
        gate="all",
        evaluator_overrides={
            "selected_transformer": _fake_eval("bug"),
            "classical": _fake_eval("question"),
            "llm_baseline_predictions": _fake_eval("bug"),
        },
    )

    assert exit_code == 1
    assert report["blocking_failure"] is True
    assert report["models"]["classical"]["status"] == "FAIL"


def _write_tiny_eval_inputs(tmp_path: Path) -> tuple[Path, Path]:
    golden_path = tmp_path / "golden.jsonl"
    golden_path.write_text(
        json.dumps(
            {
                "golden_id": "clf-golden-test",
                "issue_number": 1,
                "title": "Crash",
                "body_excerpt": "The process crashes.",
                "expected_label": "bug",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "\n".join(
            [
                "classification:",
                "  min_accuracy: 1.0",
                "  min_macro_f1: 0.25",
                "  min_per_class_f1:",
                "    bug: 1.0",
                "    feature: 0.0",
                "    docs: 0.0",
                "    question: 0.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return golden_path, thresholds_path


def _fake_eval(predicted_label: str):
    def evaluate(golden_rows):
        true_labels = [str(row["expected_label"]) for row in golden_rows]
        predicted_labels = [predicted_label for _ in golden_rows]
        return {
            "predictions": [
                {
                    "golden_id": row["golden_id"],
                    "issue_number": row["issue_number"],
                    "expected_label": row["expected_label"],
                    "predicted_label": predicted_label,
                    "confidence": None,
                }
                for row in golden_rows
            ],
            "metrics": compute_metrics(true_labels, predicted_labels),
            "missing_prediction_count": 0,
        }

    return evaluate
