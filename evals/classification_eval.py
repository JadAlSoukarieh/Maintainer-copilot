#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL_SERVER_ROOT = ROOT / "services" / "model-server"
if str(MODEL_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(MODEL_SERVER_ROOT))

from maintcopilot_model_server.domain.schemas import ClassifyRequest  # noqa: E402
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader  # noqa: E402
from maintcopilot_model_server.infra.config import Settings  # noqa: E402
from maintcopilot_model_server.services.classifier_service import ClassifierService  # noqa: E402


LABEL_ORDER = ("bug", "feature", "docs", "question")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the selected classifier on the classification golden set.")
    parser.add_argument("--golden-path", default="data/golden/classification_golden.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--report-path", default="reports/eval_report.json")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_thresholds(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = payload.get("classification")
    if not isinstance(section, dict):
        raise ValueError("Threshold file is missing a classification section.")
    return section


def compute_metrics(true_labels: list[str], predicted_labels: list[str]) -> dict[str, Any]:
    if len(true_labels) != len(predicted_labels):
        raise ValueError("True labels and predicted labels must have the same length.")
    if not true_labels:
        raise ValueError("At least one golden example is required.")

    label_to_index = {label: index for index, label in enumerate(LABEL_ORDER)}
    matrix = [[0 for _ in LABEL_ORDER] for _ in LABEL_ORDER]
    for truth, predicted in zip(true_labels, predicted_labels, strict=True):
        matrix[label_to_index[truth]][label_to_index[predicted]] += 1

    total = len(true_labels)
    correct = sum(1 for truth, predicted in zip(true_labels, predicted_labels, strict=True) if truth == predicted)
    per_class_f1: dict[str, float] = {}
    weighted_total = 0.0

    for label in LABEL_ORDER:
        index = label_to_index[label]
        tp = matrix[index][index]
        fp = sum(row[index] for row in matrix) - tp
        fn = sum(matrix[index]) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = sum(matrix[index])
        per_class_f1[label] = f1
        weighted_total += f1 * support

    return {
        "accuracy": correct / total,
        "macro_f1": sum(per_class_f1.values()) / len(LABEL_ORDER),
        "per_class_f1": per_class_f1,
        "confusion_matrix": {"labels": list(LABEL_ORDER), "matrix": matrix},
        "weighted_f1": weighted_total / total,
    }


def evaluate_thresholds(metrics: dict[str, Any], thresholds: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    min_accuracy = float(thresholds.get("min_accuracy", 0.0))
    min_macro_f1 = float(thresholds.get("min_macro_f1", 0.0))
    if metrics["accuracy"] < min_accuracy:
        failures.append(f"accuracy {metrics['accuracy']:.4f} < {min_accuracy:.4f}")
    if metrics["macro_f1"] < min_macro_f1:
        failures.append(f"macro_f1 {metrics['macro_f1']:.4f} < {min_macro_f1:.4f}")

    per_class_thresholds = thresholds.get("min_per_class_f1", {})
    if isinstance(per_class_thresholds, dict):
        for label in LABEL_ORDER:
            required = float(per_class_thresholds.get(label, 0.0))
            actual = float(metrics["per_class_f1"][label])
            if actual < required:
                failures.append(f"{label} f1 {actual:.4f} < {required:.4f}")
    return failures


def build_classifier_service() -> ClassifierService:
    settings = Settings()
    loader = ArtifactLoader(
        settings.classifier_artifact_dir,
        model_dir=settings.classifier_model_dir,
        require_artifacts=settings.classifier_require_artifacts,
        max_length=settings.classifier_max_length,
    )
    return ClassifierService(loader)


def run_eval(golden_path: Path, thresholds_path: Path, report_path: Path) -> tuple[int, dict[str, Any]]:
    golden_rows = load_jsonl(golden_path)
    thresholds = load_thresholds(thresholds_path)
    service = build_classifier_service()

    predictions: list[dict[str, Any]] = []
    true_labels: list[str] = []
    predicted_labels: list[str] = []
    for row in golden_rows:
        response = service.classify(
            ClassifyRequest(title=row["title"], body=row.get("body_excerpt", "")),
        )
        true_label = str(row["expected_label"])
        predicted_label = str(response.label)
        true_labels.append(true_label)
        predicted_labels.append(predicted_label)
        predictions.append(
            {
                "golden_id": row["golden_id"],
                "issue_number": row["issue_number"],
                "expected_label": true_label,
                "predicted_label": predicted_label,
                "confidence": response.confidence,
            }
        )

    metrics = compute_metrics(true_labels, predicted_labels)
    failures = evaluate_thresholds(metrics, thresholds)
    report = {
        "golden_path": str(golden_path),
        "thresholds_path": str(thresholds_path),
        "report_version": "classification-golden-v1",
        "example_count": len(golden_rows),
        "thresholds": thresholds,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
            "weighted_f1": metrics["weighted_f1"],
            "per_class_f1": metrics["per_class_f1"],
            "confusion_matrix": metrics["confusion_matrix"],
        },
        "predictions": predictions,
        "passed": not failures,
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return (0 if not failures else 1), report


def main() -> int:
    args = parse_args()
    exit_code, report = run_eval(
        golden_path=(ROOT / args.golden_path).resolve(),
        thresholds_path=(ROOT / args.thresholds_path).resolve(),
        report_path=(ROOT / args.report_path).resolve(),
    )

    print("Classification golden eval")
    print(f"Examples: {report['example_count']}")
    print(f"Accuracy: {report['metrics']['accuracy']:.4f}")
    print(f"Macro-F1: {report['metrics']['macro_f1']:.4f}")
    for label in LABEL_ORDER:
        print(f"{label} F1: {report['metrics']['per_class_f1'][label]:.4f}")
    if report["passed"]:
        print("Threshold gate: PASS")
    else:
        print("Threshold gate: FAIL")
        for failure in report["failures"]:
            print(f"- {failure}")
    print(f"Report: {args.report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
