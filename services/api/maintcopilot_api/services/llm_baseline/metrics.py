from __future__ import annotations

from collections import Counter
from typing import Any


LABEL_ORDER = ("bug", "feature", "docs", "question")


def estimate_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
) -> float:
    input_cost = (input_tokens / 1_000_000) * input_price_per_mtok
    output_cost = (output_tokens / 1_000_000) * output_price_per_mtok
    return round(input_cost + output_cost, 10)


def compute_metrics(true_labels: list[str], predicted_labels: list[str]) -> dict[str, Any]:
    if len(true_labels) != len(predicted_labels):
        raise ValueError("True labels and predicted labels must have the same length.")
    if not true_labels:
        raise ValueError("At least one prediction is required to compute metrics.")

    matrix = [[0 for _ in LABEL_ORDER] for _ in LABEL_ORDER]
    label_to_index = {label: index for index, label in enumerate(LABEL_ORDER)}
    for truth, predicted in zip(true_labels, predicted_labels, strict=True):
        matrix[label_to_index[truth]][label_to_index[predicted]] += 1

    total = len(true_labels)
    correct = sum(1 for truth, predicted in zip(true_labels, predicted_labels, strict=True) if truth == predicted)
    per_class_f1: dict[str, float] = {}
    weighted_f1_total = 0.0

    for label in LABEL_ORDER:
        index = label_to_index[label]
        tp = matrix[index][index]
        fp = sum(row[index] for row in matrix) - tp
        fn = sum(matrix[index]) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class_f1[label] = f1
        weighted_f1_total += f1 * sum(matrix[index])

    macro_f1 = sum(per_class_f1.values()) / len(LABEL_ORDER)
    weighted_f1 = weighted_f1_total / total

    return {
        "accuracy": correct / total,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class_f1": per_class_f1,
        "confusion_matrix": {
            "labels": list(LABEL_ORDER),
            "matrix": matrix,
        },
    }


def build_metrics_report(
    *,
    predictions: list[dict[str, Any]],
    data_hash: str | None,
    model_name: str,
    prompt_version: str,
    run_id: str,
    dry_run: bool,
) -> dict[str, Any]:
    true_labels = [str(item["true_label"]) for item in predictions]
    predicted_labels = [str(item["predicted_label"]) for item in predictions]
    metrics = compute_metrics(true_labels, predicted_labels)

    latencies = [float(item.get("latency_ms", 0.0) or 0.0) for item in predictions]
    total_latency_ms = sum(latencies)
    metrics["latency"] = {
        "total_seconds": total_latency_ms / 1000,
        "avg_ms_per_issue": total_latency_ms / len(predictions),
        "num_examples": len(predictions),
    }

    return {
        "model_type": "llm_baseline",
        "model_name": model_name,
        "data_hash": data_hash,
        "test_count": len(predictions),
        "prompt_version": prompt_version,
        "run_id": run_id,
        "dry_run": dry_run,
        "test": metrics,
    }


def build_cost_report(
    *,
    predictions: list[dict[str, Any]],
    model_name: str,
    prompt_version: str,
    run_id: str,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
    dry_run: bool,
) -> dict[str, Any]:
    total_input_tokens = sum(int(item.get("input_tokens", 0) or 0) for item in predictions)
    total_output_tokens = sum(int(item.get("output_tokens", 0) or 0) for item in predictions)
    total_estimated_cost_usd = round(sum(float(item.get("estimated_cost_usd", 0.0) or 0.0) for item in predictions), 10)

    return {
        "model_name": model_name,
        "prompt_version": prompt_version,
        "run_id": run_id,
        "input_price_per_mtok": input_price_per_mtok,
        "output_price_per_mtok": output_price_per_mtok,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_estimated_cost_usd": total_estimated_cost_usd,
        "processed_examples": len(predictions),
        "dry_run": dry_run,
    }


def summarize_predictions(predictions: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(item["predicted_label"]) for item in predictions))
