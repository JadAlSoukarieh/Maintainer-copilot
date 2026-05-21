#!/usr/bin/env python3
"""Log the frozen RoBERTa classifier training run to local MLflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = REPO_ROOT / "artifacts/classifier/transformer/metrics.json"
ARGS_PATH = REPO_ROOT / "artifacts/classifier/transformer/training_args.json"
COMPARISON_PATH = REPO_ROOT / "artifacts/classifier/comparison/model_comparison.md"
MLFLOW_TRACKING_URI = str(REPO_ROOT / "mlruns")


def main() -> int:
    try:
        import mlflow
    except ImportError:
        print('MLflow is not installed. Install with: ./.venv/bin/python -m pip install "mlflow>=2.14,<3.0"')
        return 2

    metrics = _load_json(METRICS_PATH)
    args = _load_json(ARGS_PATH)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("nodejs-issue-classifier")

    with mlflow.start_run(run_name="roberta-base-finetune"):
        mlflow.log_param("base_model", metrics.get("base_model", "roberta-base"))
        mlflow.log_param("learning_rate", args.get("learning_rate", 1e-5))
        mlflow.log_param("num_train_epochs", args.get("num_train_epochs", 5))
        mlflow.log_param("per_device_train_batch_size", args.get("per_device_train_batch_size", 8))
        mlflow.log_param("per_device_eval_batch_size", args.get("per_device_eval_batch_size", 16))
        mlflow.log_param("weight_decay", args.get("weight_decay", 0.01))
        mlflow.log_param("warmup_steps", args.get("warmup_steps", 0))
        mlflow.log_param("optimizer", args.get("optim", "adamw_torch_fused"))
        mlflow.log_param("max_length", metrics.get("max_length", 512))
        mlflow.log_param("train_count", metrics.get("train_count"))
        mlflow.log_param("val_count", metrics.get("val_count"))
        mlflow.log_param("test_count", metrics.get("test_count"))
        mlflow.log_param("seed", args.get("seed", 42))

        _log_split_metrics(mlflow, "val", metrics.get("val", {}))
        _log_split_metrics(mlflow, "test", metrics.get("test", {}))
        latency = metrics.get("test", {}).get("latency", {})
        _log_metric_if_present(mlflow, "avg_latency_ms", latency.get("avg_ms_per_issue"))
        _log_metric_if_present(mlflow, "train_time_seconds", metrics.get("train_time_seconds"))

        mlflow.log_artifact(str(METRICS_PATH), artifact_path="classifier")
        mlflow.log_artifact(str(ARGS_PATH), artifact_path="classifier")
        if COMPARISON_PATH.exists():
            mlflow.log_artifact(str(COMPARISON_PATH), artifact_path="classifier")

    print("MLflow run logged.")
    print(f"View at: mlflow ui --backend-store-uri {MLFLOW_TRACKING_URI} --port 5000")
    print("Then open http://localhost:5000")
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _log_split_metrics(mlflow: Any, split: str, values: dict[str, Any]) -> None:
    _log_metric_if_present(mlflow, f"{split}_accuracy", values.get("accuracy"))
    _log_metric_if_present(mlflow, f"{split}_macro_f1", values.get("macro_f1"))
    _log_metric_if_present(mlflow, f"{split}_weighted_f1", values.get("weighted_f1"))
    for label, f1_score in (values.get("per_class_f1") or {}).items():
        _log_metric_if_present(mlflow, f"{split}_f1_{label}", f1_score)


def _log_metric_if_present(mlflow: Any, key: str, value: Any) -> None:
    if value is not None:
        mlflow.log_metric(key, float(value))


if __name__ == "__main__":
    raise SystemExit(main())
