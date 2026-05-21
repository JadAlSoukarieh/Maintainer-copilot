# RoBERTa Transformer Classifier Model Card

## Purpose

This model classifies closed GitHub issues from `nodejs/node` into one of four triage labels:

- bug
- feature
- docs
- question

It is part of the Week 7 Maintainer's Copilot classifier comparison.

## Architecture

Architecture: Transformer encoder for sequence classification

Base model: `roberta-base`

Fine-tuned model: RoBERTa sequence classification head

Max sequence length: 512

## Label Mapping

Label IDs:

{
  "bug": 0,
  "feature": 1,
  "docs": 2,
  "question": 3
}

Original maintainer labels were mapped as:

{
  "confirmed-bug": "bug",
  "feature request": "feature",
  "doc": "docs",
  "question": "question"
}

## Freeze Policy

No layers were frozen.

All RoBERTa encoder layers and the classification head were fine-tuned. This was chosen because the classifier needs to learn repo-specific issue language and distinguish ambiguous cases such as bug reports versus questions.

## Hyperparameters

{
  "learning_rate": 1e-05,
  "batch_size_train": 8,
  "batch_size_eval": 16,
  "num_train_epochs": 5,
  "weight_decay": 0.01,
  "class_weighted_loss": true,
  "fp16": false,
  "seed": 42
}

## Dataset

Repository: `nodejs/node`

Split strategy: global chronological 70/15/15

Train count: 914

Validation count: 196

Test count: 196

Data hash: `db3e1d356b3202533fc16fe75a21fdf40c9a5c060a19172ec3d403398f7c6d27`

## Final Validation Metrics

{
  "accuracy": 0.7397959183673469,
  "macro_f1": 0.6995210802419041,
  "weighted_f1": 0.7479278733014781,
  "per_class_f1": {
    "bug": 0.4782608695652174,
    "feature": 0.8034188034188035,
    "docs": 0.7532467532467533,
    "question": 0.7631578947368421
  }
}

## Final Test Metrics

{
  "accuracy": 0.7244897959183674,
  "macro_f1": 0.7115728715728715,
  "weighted_f1": 0.7338525193627234,
  "per_class_f1": {
    "bug": 0.5555555555555556,
    "feature": 0.6933333333333334,
    "docs": 0.8571428571428571,
    "question": 0.7402597402597403
  },
  "latency": {
    "total_seconds": 7.16349550599989,
    "avg_ms_per_issue": 36.54844645918311,
    "num_examples": 196
  }
}

## Model Artifact SHA-256

`2b52851580881cf773af38be1a41df965a7b9c79c98f73ff905d28f92ae35e0b`

## Runtime Note

The model was trained in Colab because fine-tuning requires GPU resources. The production project does not depend on Colab at runtime. The Docker stack should load this frozen artifact, verify its hash against this model card, and run CI evals against golden examples without retraining.

## Training run

Logged to local MLflow for demo/review use. To view:

```bash
python scripts/log_training_run.py
mlflow ui --backend-store-uri mlruns --port 5000
```

Key training config:

- Base model: `roberta-base`
- Epochs: 5
- Learning rate: `1e-5`
- Train batch size: 8
- Max length: 512
- Optimizer: AdamW fused
- Weight decay: 0.01
- Best metric: `macro_f1` (`eval_strategy=epoch`)
- Train time: approximately 644 seconds on Colab GPU
