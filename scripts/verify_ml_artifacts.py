#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = {
    "dataset": [
        "data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl",
        "data/raw/nodejs_node_capped_fetch_metadata.json",
        "data/processed/train.jsonl",
        "data/processed/val.jsonl",
        "data/processed/test.jsonl",
        "data/processed/excluded_issues.jsonl",
        "data/processed/label_mapping.json",
        "data/processed/data_hash.txt",
        "data/processed/split_manifest.json",
        "data/golden/classification_golden.jsonl",
    ],
    "classical": [
        "artifacts/classifier/classical/model.joblib",
        "artifacts/classifier/classical/metrics.json",
        "artifacts/classifier/classical/confusion_matrix.json",
        "artifacts/classifier/classical/test_predictions.jsonl",
    ],
    "transformer": [
        "artifacts/classifier/transformer/model/config.json",
        "artifacts/classifier/transformer/model/model.safetensors",
        "artifacts/classifier/transformer/model/tokenizer.json",
        "artifacts/classifier/transformer/model/tokenizer_config.json",
        "artifacts/classifier/transformer/model/special_tokens_map.json",
        "artifacts/classifier/transformer/model/vocab.json",
        "artifacts/classifier/transformer/model/merges.txt",
        "artifacts/classifier/transformer/metrics.json",
        "artifacts/classifier/transformer/confusion_matrix.json",
        "artifacts/classifier/transformer/test_predictions.jsonl",
        "artifacts/classifier/transformer/model_card.md",
        "artifacts/classifier/transformer/training_args.json",
    ],
    "llm_baseline": [
        "artifacts/classifier/llm_baseline/predictions.jsonl",
        "artifacts/classifier/llm_baseline/metrics.json",
        "artifacts/classifier/llm_baseline/cost_report.json",
    ],
    "comparison": [
        "artifacts/classifier/comparison/classification_report.json",
        "artifacts/classifier/comparison/confusion_matrix.json",
        "artifacts/classifier/comparison/model_comparison.md",
    ],
    "reports": [
        "reports/dataset_validation.md",
        "reports/training_run_summary.md",
    ],
}

REQUIRED_CORE_CATEGORIES = {"dataset", "classical", "transformer", "comparison", "reports"}
SHA_TARGETS = {
    "artifacts/classifier/classical/model.joblib",
    "artifacts/classifier/transformer/model/model.safetensors",
}


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        print(f"Could not parse JSON from {path}: {exc}", file=sys.stderr)
        return None


def extract_macro_f1(payload: dict | None) -> object:
    if not payload:
        return None
    if "macro_f1" in payload:
        return payload["macro_f1"]
    metrics = payload.get("metrics")
    if isinstance(metrics, dict) and "macro_f1" in metrics:
        return metrics["macro_f1"]
    return None


def print_missing(missing: dict[str, list[str]]) -> None:
    print("Missing files by category:")
    for category, paths in missing.items():
        print(f"- {category}:")
        if paths:
            for path in paths:
                print(f"  - {path}")
        else:
            print("  - none")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify expected ML dataset and artifact files.")
    parser.add_argument(
        "--allow-missing-llm",
        action="store_true",
        help="Do not fail verification when LLM baseline files are missing.",
    )
    args = parser.parse_args()

    missing: dict[str, list[str]] = {}
    for category, rel_paths in EXPECTED_FILES.items():
        category_missing = []
        for rel_path in rel_paths:
            if not (ROOT / rel_path).exists():
                category_missing.append(rel_path)
        missing[category] = category_missing

    print_missing(missing)
    print()

    print("Detected hashes:")
    for rel_path in sorted(SHA_TARGETS):
        path = ROOT / rel_path
        if path.exists():
            print(f"- {rel_path}: {sha256_for_file(path)}")
        else:
            print(f"- {rel_path}: missing")
    print()

    print("Metric summary:")
    classical_metrics = load_json(ROOT / "artifacts/classifier/classical/metrics.json")
    transformer_metrics = load_json(ROOT / "artifacts/classifier/transformer/metrics.json")
    llm_metrics = load_json(ROOT / "artifacts/classifier/llm_baseline/metrics.json")
    print(f"- classical macro-F1: {extract_macro_f1(classical_metrics)}")
    print(f"- transformer macro-F1: {extract_macro_f1(transformer_metrics)}")
    print(f"- LLM macro-F1: {extract_macro_f1(llm_metrics)}")
    print()

    data_hash_path = ROOT / "data/processed/data_hash.txt"
    if data_hash_path.exists():
        print("Processed data hash:")
        print(data_hash_path.read_text(encoding="utf-8").strip())
    else:
        print("Processed data hash:")
        print("missing")

    required_categories = set(REQUIRED_CORE_CATEGORIES)
    if not args.allow_missing_llm:
        required_categories.add("llm_baseline")

    failed_categories = [category for category in required_categories if missing.get(category)]
    if failed_categories:
        print()
        print("Verification failed. Missing required core files in categories:", ", ".join(sorted(failed_categories)), file=sys.stderr)
        return 1

    print()
    print("Verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
