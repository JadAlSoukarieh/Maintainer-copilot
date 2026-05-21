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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MODEL_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(MODEL_SERVER_ROOT))

from maintcopilot_model_server.domain.schemas import ClassifyRequest  # noqa: E402
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader  # noqa: E402
from maintcopilot_model_server.infra.config import Settings as ModelSettings  # noqa: E402
from maintcopilot_model_server.services.classifier_service import ClassifierService  # noqa: E402


LABEL_ORDER = ("bug", "feature", "docs", "question")
MODEL_CHOICES = ("selected_transformer", "classical", "llm_baseline_predictions", "all")
GATE_CHOICES = ("primary", "all", "none")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate classification golden set across frozen model families.")
    parser.add_argument("--golden-path", default="data/golden/classification_golden.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--report-path", default="reports/eval_report.json")
    parser.add_argument("--model", default="selected_transformer", choices=MODEL_CHOICES)
    parser.add_argument(
        "--gate",
        default="primary",
        choices=GATE_CHOICES,
        help="Gate policy: primary gates only the deployed transformer, all gates every requested model, none reports only.",
    )
    parser.add_argument(
        "--strict-baselines",
        action="store_true",
        help="Alias for --gate all. Makes classical and LLM baseline failures block.",
    )
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


def build_transformer_service() -> ClassifierService:
    settings = ModelSettings()
    loader = ArtifactLoader(
        settings.classifier_artifact_dir,
        model_dir=settings.classifier_model_dir,
        require_artifacts=settings.classifier_require_artifacts,
        max_length=settings.classifier_max_length,
    )
    return ClassifierService(loader)


def evaluate_selected_transformer(golden_rows: list[dict[str, Any]]) -> dict[str, Any]:
    service = build_transformer_service()
    predictions: list[dict[str, Any]] = []
    true_labels: list[str] = []
    predicted_labels: list[str] = []
    for row in golden_rows:
        response = service.classify(ClassifyRequest(title=row["title"], body=row.get("body_excerpt", "")))
        predictions.append(
            {
                "golden_id": row["golden_id"],
                "issue_number": row["issue_number"],
                "expected_label": row["expected_label"],
                "predicted_label": response.label,
                "confidence": response.confidence,
            }
        )
        true_labels.append(str(row["expected_label"]))
        predicted_labels.append(str(response.label))
    metrics = compute_metrics(true_labels, predicted_labels)
    return {"predictions": predictions, "metrics": metrics, "missing_prediction_count": 0}


def evaluate_classical(golden_rows: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        import joblib
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("joblib is required for classical golden eval.") from exc

    model = joblib.load(ROOT / "artifacts/classifier/classical/model.joblib")
    inputs = [_classical_input_text(row) for row in golden_rows]
    predicted = [str(label) for label in model.predict(inputs)]
    predictions = [
        {
            "golden_id": row["golden_id"],
            "issue_number": row["issue_number"],
            "expected_label": row["expected_label"],
            "predicted_label": label,
            "confidence": None,
        }
        for row, label in zip(golden_rows, predicted, strict=True)
    ]
    metrics = compute_metrics([str(row["expected_label"]) for row in golden_rows], predicted)
    return {"predictions": predictions, "metrics": metrics, "missing_prediction_count": 0}


def evaluate_llm_predictions(golden_rows: list[dict[str, Any]]) -> dict[str, Any]:
    prediction_path = ROOT / "artifacts/classifier/llm_baseline/predictions.jsonl"
    if not prediction_path.exists():
        return {
            "predictions": [],
            "metrics": None,
            "missing_prediction_count": len(golden_rows),
            "coverage": 0.0,
            "missing_issue_numbers": [row["issue_number"] for row in golden_rows],
        }
    llm_rows = load_jsonl(prediction_path)
    by_issue_number = {row.get("issue_number"): row for row in llm_rows}
    matched_predictions: list[dict[str, Any]] = []
    true_labels: list[str] = []
    predicted_labels: list[str] = []
    missing_issue_numbers: list[int] = []
    for row in golden_rows:
        llm_prediction = by_issue_number.get(row["issue_number"])
        if not llm_prediction:
            missing_issue_numbers.append(int(row["issue_number"]))
            continue
        predicted_label = str(llm_prediction.get("predicted_label", "")).strip()
        if predicted_label not in LABEL_ORDER:
            missing_issue_numbers.append(int(row["issue_number"]))
            continue
        matched_predictions.append(
            {
                "golden_id": row["golden_id"],
                "issue_number": row["issue_number"],
                "expected_label": row["expected_label"],
                "predicted_label": predicted_label,
                "confidence": None,
            }
        )
        true_labels.append(str(row["expected_label"]))
        predicted_labels.append(predicted_label)

    metrics = compute_metrics(true_labels, predicted_labels) if true_labels else None
    return {
        "predictions": matched_predictions,
        "metrics": metrics,
        "missing_prediction_count": len(missing_issue_numbers),
        "coverage": len(matched_predictions) / len(golden_rows) if golden_rows else 0.0,
        "missing_issue_numbers": missing_issue_numbers,
    }


def run_eval(
    golden_path: Path,
    thresholds_path: Path,
    report_path: Path,
    *,
    model: str = "selected_transformer",
    gate: str = "primary",
    evaluator_overrides: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    golden_rows = load_jsonl(golden_path)
    thresholds = load_thresholds(thresholds_path)
    selected_key = "selected_transformer"
    requested_models = [model] if model != "all" else ["selected_transformer", "classical", "llm_baseline_predictions"]

    evaluators = {
        "selected_transformer": evaluate_selected_transformer,
        "classical": evaluate_classical,
        "llm_baseline_predictions": evaluate_llm_predictions,
    }
    if evaluator_overrides:
        evaluators.update(evaluator_overrides)

    model_reports: dict[str, Any] = {}
    blocking_failure = False
    baseline_failures: list[str] = []
    for model_name in requested_models:
        result = evaluators[model_name](golden_rows)
        metrics = result.get("metrics")
        failures = evaluate_thresholds(metrics, thresholds) if metrics else ["no predictions available for evaluation"]
        threshold_passed = not failures
        blocking = _is_blocking_model(model_name=model_name, gate=gate, selected_key=selected_key)
        if not threshold_passed and blocking:
            blocking_failure = True
        if not threshold_passed and not blocking:
            baseline_failures.append(model_name)
        status = _model_status(threshold_passed=threshold_passed, blocking=blocking)
        model_reports[model_name] = {
            "metrics": metrics,
            "predictions": result.get("predictions", []),
            "missing_prediction_count": result.get("missing_prediction_count", 0),
            "coverage": result.get("coverage", 1.0),
            "missing_issue_numbers": result.get("missing_issue_numbers", []),
            "passed": threshold_passed,
            "threshold_passed": threshold_passed,
            "blocking": blocking,
            "status": status,
            "failures": failures,
            "selected_model": model_name == selected_key,
        }

    if model == "all":
        report = {
            "golden_path": str(golden_path),
            "thresholds_path": str(thresholds_path),
            "report_version": "classification-golden-v2",
            "example_count": len(golden_rows),
            "thresholds": thresholds,
            "requested_model": model,
            "selected_model": selected_key,
            "gating_model": selected_key,
            "gate_policy": gate,
            "blocking_failure": blocking_failure,
            "baseline_failures": baseline_failures,
            "models": model_reports,
            "passed": not blocking_failure,
        }
    else:
        single = model_reports[requested_models[0]]
        report = {
            "golden_path": str(golden_path),
            "thresholds_path": str(thresholds_path),
            "report_version": "classification-golden-v1",
            "example_count": len(golden_rows),
            "thresholds": thresholds,
            "metrics": single["metrics"],
            "predictions": single["predictions"],
            "passed": not blocking_failure,
            "threshold_passed": single["threshold_passed"],
            "status": single["status"],
            "blocking": single["blocking"],
            "failures": single["failures"],
            "requested_model": model,
            "selected_model": selected_key,
            "gating_model": selected_key,
            "gate_policy": gate,
            "blocking_failure": blocking_failure,
            "baseline_failures": baseline_failures,
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return (0 if report["passed"] else 1), report


def main() -> int:
    args = parse_args()
    gate = "all" if args.strict_baselines else args.gate
    default_report_path = "reports/classification_golden_eval_all.json" if args.model == "all" else args.report_path
    exit_code, report = run_eval(
        golden_path=(ROOT / args.golden_path).resolve(),
        thresholds_path=(ROOT / args.thresholds_path).resolve(),
        report_path=(ROOT / default_report_path).resolve(),
        model=args.model,
        gate=gate,
    )

    print("Classification golden eval")
    print(f"Examples: {report['example_count']}")
    print(f"Requested model mode: {args.model}")
    print(f"Gate policy: {gate}")
    print(f"Gating model: {report.get('gating_model', 'selected_transformer')}")
    model_entries = report.get("models") or {args.model: report}
    for model_name, model_report in model_entries.items():
        print(f"\n[{model_name}]")
        metrics = model_report.get("metrics")
        if metrics:
            print(f"Accuracy: {metrics['accuracy']:.4f}")
            print(f"Macro-F1: {metrics['macro_f1']:.4f}")
            for label in LABEL_ORDER:
                print(f"{label} F1: {metrics['per_class_f1'][label]:.4f}")
        else:
            print("No metrics available.")
        print(f"Missing predictions: {model_report.get('missing_prediction_count', 0)}")
        print(f"Status: {model_report.get('status', 'PASS' if model_report.get('passed') else 'FAIL')}")
        if model_report.get("failures"):
            print("Failures: " + "; ".join(model_report["failures"]))
    print("\nBlocking result: PASS" if not report.get("blocking_failure") else "\nBlocking result: FAIL")
    print(f"\nReport: {default_report_path}")
    from evals._minio_upload import try_upload_report  # noqa: PLC0415
    try_upload_report((ROOT / default_report_path).resolve())
    return exit_code


def _classical_input_text(row: dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip()
    body = str(row.get("body_excerpt") or "").strip()
    return f"{title}\n\n{body}".strip()


def _is_blocking_model(*, model_name: str, gate: str, selected_key: str) -> bool:
    if gate == "none":
        return False
    if gate == "all":
        return True
    return model_name == selected_key


def _model_status(*, threshold_passed: bool, blocking: bool) -> str:
    if threshold_passed:
        return "PASS"
    return "FAIL" if blocking else "WARN"


if __name__ == "__main__":
    raise SystemExit(main())
