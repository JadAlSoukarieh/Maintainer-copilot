# LLM Baseline Outputs

Expected files in this directory:

- `predictions.jsonl`
- `metrics.json`
- `cost_report.json`

This directory is optional during early local setup. It is reserved for prompt-based baseline outputs when those runs exist.

- Produced by: later Colab or evaluation scripts
- Consumed by: comparison reporting and verification scripts

The verification script supports `--allow-missing-llm` because these files may not exist yet.

