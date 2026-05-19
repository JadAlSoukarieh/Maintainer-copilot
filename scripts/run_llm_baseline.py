#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SERVICE_ROOT = ROOT / "services" / "api"
if str(API_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(API_SERVICE_ROOT))

from maintcopilot_api.infra.anthropic_client import (  # noqa: E402
    AnthropicClassifierClient,
    AnthropicKeyResolutionError,
    AnthropicRequestError,
    resolve_anthropic_api_key,
)
from maintcopilot_api.infra.config import Settings  # noqa: E402
from maintcopilot_api.infra.vault import VaultClient  # noqa: E402
from maintcopilot_api.services.llm_baseline.runner import run_baseline  # noqa: E402


def load_local_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Claude LLM baseline issue classifier.")
    parser.add_argument("--test-path", default="data/processed/test.jsonl")
    parser.add_argument("--output-dir", default="artifacts/classifier/llm_baseline")
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", dest="resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-env-key", action="store_true")
    parser.add_argument("--max-body-chars", type=int, default=6000)
    parser.add_argument("--input-price-per-mtok", type=float, default=1.00)
    parser.add_argument("--output-price-per-mtok", type=float, default=5.00)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_local_env_file(ROOT / ".env.local")
    settings = Settings()
    model_name = args.model_name or settings.anthropic_model_name
    test_path = (ROOT / args.test_path).resolve()
    output_dir = (ROOT / args.output_dir).resolve()

    classifier_client: AnthropicClassifierClient | None = None
    if not args.dry_run:
        vault_client = VaultClient(addr=settings.vault_addr, token=settings.vault_token)
        try:
            api_key = resolve_anthropic_api_key(
                settings,
                vault_client,
                allow_env_fallback=args.allow_env_key,
                for_cli=True,
            )
        except AnthropicKeyResolutionError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        try:
            classifier_client = AnthropicClassifierClient(api_key=api_key, model_name=model_name)
        except AnthropicRequestError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    try:
        summary = run_baseline(
            test_path=test_path,
            output_dir=output_dir,
            model_name=model_name,
            limit=args.limit,
            resume=args.resume,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            max_body_chars=args.max_body_chars,
            input_price_per_mtok=args.input_price_per_mtok,
            output_price_per_mtok=args.output_price_per_mtok,
            classifier_client=classifier_client,
        )
    except (AnthropicRequestError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("LLM baseline completed.")
    print(f"Predictions: {summary['predictions_path']}")
    print(f"Metrics: {summary['metrics_path']}")
    print(f"Cost report: {summary['cost_report_path']}")
    print(f"Processed examples: {summary['processed_examples']}")
    print(f"New predictions: {summary['new_predictions']}")
    print(f"Model: {summary['model_name']}")
    print(f"Dry run: {summary['dry_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
