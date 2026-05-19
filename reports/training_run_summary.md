# Training Run Summary

## Dataset context

- Repository: `nodejs/node`
- Data hash: `db3e1d356b3202533fc16fe75a21fdf40c9a5c060a19172ec3d403398f7c6d27`
- Test examples: 196

## Classical baseline

Model: TF-IDF + Logistic Regression

- accuracy: 0.7041
- macro-F1: 0.6681
- weighted-F1: 0.7061
- bug F1: 0.4444
- average latency: ~0.80 ms / issue

This baseline remains useful because it is simple, deterministic, and substantially faster than the transformer runs.

## Archived transformer experiment

An earlier DistilBERT experiment is part of the archived Colab training history, not a deployable artifact bundle in this repo.

- model: DistilBERT
- accuracy: 0.7092
- macro-F1: 0.6851
- bug F1: 0.5085
- average latency: ~3.81 ms / issue

This summary is retained for comparison only. It is not the final served classifier artifact.

## Final transformer

Model: RoBERTa-base sequence classifier

- accuracy: 0.7245
- macro-F1: 0.7116
- weighted-F1: 0.7339
- bug F1: 0.5556
- average latency: ~36.55 ms / issue
- model hash: `2b52851580881cf773af38be1a41df965a7b9c79c98f73ff905d28f92ae35e0b`

The local deployable transformer artifact is the Hugging Face export under `artifacts/classifier/transformer/model/`.

## Deployment decision

- RoBERTa is the selected final transformer because it achieved the best macro-F1 and the best bug F1 among the stored deterministic classifier results.
- The classical TF-IDF + Logistic Regression model remains useful as a fallback because it is much faster and easier to run in constrained environments.
- The final deployment choice may still be revisited after the LLM baseline is available, but the LLM baseline is expected to remain a comparison or generation aid rather than the primary deterministic issue classifier.

## Known weakness

The main remaining weakness is bug versus question confusion. That pattern is visible in the class-level F1 scores and remains the most important class-boundary risk to watch in later evals.

## LLM baseline status

LLM baseline metrics are still pending. No LLM baseline numbers are declared here because the corresponding outputs have not been copied into the repo yet.
