from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from maintcopilot_api.infra.anthropic_client import AnthropicClassificationResponse, AnthropicClassifierClient
from maintcopilot_api.services.llm_baseline.metrics import build_cost_report, build_metrics_report, estimate_cost_usd
from maintcopilot_api.services.llm_baseline.parsing import PROMPT_VERSION, parse_label_response


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "prompts").exists() and (parent / "data").exists():
            return parent
    raise RuntimeError("Could not determine repository root.")


def load_prompt_template() -> str:
    prompt_path = find_repo_root() / "prompts" / "llm_baseline_classifier.md"
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(*, title: str, body: str) -> str:
    return load_prompt_template().format(title=title.strip(), body=body.strip())


def load_test_rows(test_path: Path, *, limit: int | None = None, max_body_chars: int = 6000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with test_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            rows.append(
                {
                    "issue_id": str(payload["issue_id"]),
                    "issue_number": int(payload["issue_number"]),
                    "url": payload["url"],
                    "title": payload.get("title", "") or "",
                    "body": (payload.get("body", "") or "")[:max_body_chars],
                    "true_label": payload["label"],
                }
            )
            if limit is not None and len(rows) >= limit:
                break
    return rows


def make_resume_key(payload: dict[str, Any]) -> str:
    issue_number = payload.get("issue_number")
    if issue_number is not None:
        return f"issue_number:{issue_number}"
    return f"issue_id:{payload['issue_id']}"


def load_existing_predictions(predictions_path: Path) -> list[dict[str, Any]]:
    if not predictions_path.exists():
        return []
    with predictions_path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_existing_predictions(
    predictions: list[dict[str, Any]],
    *,
    dry_run: bool,
    prompt_version: str,
    requested_model_name: str,
) -> str | None:
    if not predictions:
        return None

    run_ids = {str(item.get("run_id")) for item in predictions}
    if len(run_ids) != 1:
        raise ValueError("Existing predictions contain multiple run_ids. Use --overwrite or a clean output directory.")

    existing_prompt_versions = {str(item.get("prompt_version")) for item in predictions}
    if existing_prompt_versions != {prompt_version}:
        raise ValueError("Existing predictions were generated with a different prompt version.")

    existing_dry_run_flags = {bool(item.get("dry_run")) for item in predictions}
    if existing_dry_run_flags != {dry_run}:
        raise ValueError("Existing predictions were generated with a different dry_run mode.")

    existing_model_names = {str(item.get("model_name")) for item in predictions}
    if not dry_run and existing_model_names != {requested_model_name}:
        raise ValueError("Existing predictions were generated with a different model name.")

    return run_ids.pop()


def filter_pending_rows(rows: list[dict[str, Any]], existing_predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    completed = {make_resume_key(item) for item in existing_predictions}
    return [row for row in rows if make_resume_key(row) not in completed]


def deterministic_dry_run_label(*, title: str, body: str) -> str:
    text = f"{title}\n{body}".lower()
    if any(token in text for token in ("documentation", "docs", "doc:", "readme", "guide", "typo", "linkrotted")):
        return "docs"
    if any(token in text for token in ("feature request", "enhancement", "please add", "request for", "new api", "option to")):
        return "feature"
    if any(token in text for token in ("crash", "regression", "incorrect", "failing test", "memory leak", "out of memory", "fatal error")):
        return "bug"
    if "?" in text or any(token in text for token in ("how to", "is there", "can someone", "help", "usage", "debug")):
        return "question"
    return "question"


def call_dry_run_classifier(row: dict[str, Any], *, model_name: str) -> AnthropicClassificationResponse:
    label = deterministic_dry_run_label(title=row["title"], body=row["body"])
    return AnthropicClassificationResponse(
        raw_output=json.dumps({"label": label}),
        input_tokens=0,
        output_tokens=0,
        model_name=model_name,
    )


def write_predictions(path: Path, predictions: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for prediction in predictions:
            handle.write(json.dumps(prediction, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_data_hash(test_path: Path) -> str | None:
    data_hash_path = test_path.parent / "data_hash.txt"
    if not data_hash_path.exists():
        return None
    return data_hash_path.read_text(encoding="utf-8").strip()


def run_baseline(
    *,
    test_path: Path,
    output_dir: Path,
    model_name: str,
    limit: int | None,
    resume: bool,
    overwrite: bool,
    dry_run: bool,
    max_body_chars: int,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
    classifier_client: AnthropicClassifierClient | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    metrics_path = output_dir / "metrics.json"
    cost_report_path = output_dir / "cost_report.json"

    if overwrite:
        for path in (predictions_path, metrics_path, cost_report_path):
            if path.exists():
                path.unlink()

    rows = load_test_rows(test_path, limit=limit, max_body_chars=max_body_chars)
    existing_predictions = load_existing_predictions(predictions_path) if resume else []
    requested_model_name = model_name
    run_id = validate_existing_predictions(
        existing_predictions,
        dry_run=dry_run,
        prompt_version=PROMPT_VERSION,
        requested_model_name=requested_model_name,
    )
    if run_id is None:
        run_id = uuid.uuid4().hex

    pending_rows = filter_pending_rows(rows, existing_predictions) if resume else rows
    new_predictions: list[dict[str, Any]] = []

    for row in pending_rows:
        prompt = render_prompt(title=row["title"], body=row["body"])
        started_at = time.perf_counter()
        if dry_run:
            response = call_dry_run_classifier(row, model_name=f"dry-run::{model_name}")
        else:
            if classifier_client is None:
                raise RuntimeError("Anthropic classifier client is required for non-dry-run execution.")
            response = classifier_client.classify(prompt)
        latency_ms = (time.perf_counter() - started_at) * 1000
        predicted_label = parse_label_response(response.raw_output)
        estimated_cost = estimate_cost_usd(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            input_price_per_mtok=input_price_per_mtok,
            output_price_per_mtok=output_price_per_mtok,
        )
        new_predictions.append(
            {
                "run_id": run_id,
                "prompt_version": PROMPT_VERSION,
                "issue_id": row["issue_id"],
                "issue_number": row["issue_number"],
                "url": row["url"],
                "title": row["title"],
                "true_label": row["true_label"],
                "predicted_label": predicted_label,
                "raw_model_output": response.raw_output,
                "latency_ms": round(latency_ms, 3),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost_usd": estimated_cost,
                "model_name": response.model_name,
                "dry_run": dry_run,
            }
        )

    if new_predictions:
        write_predictions(predictions_path, new_predictions)

    merged_predictions = load_existing_predictions(predictions_path)
    if not merged_predictions:
        raise ValueError("No predictions were generated.")

    effective_model_name = str(merged_predictions[0]["model_name"])
    data_hash = load_data_hash(test_path)
    metrics_report = build_metrics_report(
        predictions=merged_predictions,
        data_hash=data_hash,
        model_name=effective_model_name,
        prompt_version=PROMPT_VERSION,
        run_id=run_id,
        dry_run=dry_run,
    )
    cost_report = build_cost_report(
        predictions=merged_predictions,
        model_name=effective_model_name,
        prompt_version=PROMPT_VERSION,
        run_id=run_id,
        input_price_per_mtok=input_price_per_mtok,
        output_price_per_mtok=output_price_per_mtok,
        dry_run=dry_run,
    )
    write_json(metrics_path, metrics_report)
    write_json(cost_report_path, cost_report)

    return {
        "run_id": run_id,
        "processed_examples": len(merged_predictions),
        "new_predictions": len(new_predictions),
        "predictions_path": predictions_path,
        "metrics_path": metrics_path,
        "cost_report_path": cost_report_path,
        "dry_run": dry_run,
        "model_name": effective_model_name,
    }
