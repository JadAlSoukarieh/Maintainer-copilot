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

## LLM baseline

Model: Claude Haiku 4.5

- accuracy: 0.7041
- macro-F1: 0.7112
- weighted-F1: 0.7294
- bug F1: 0.5208
- feature F1: 0.7692
- docs F1: 0.8395
- question F1: 0.7153
- average latency: ~1106.50 ms / issue
- estimated cost: ~$0.1118 for 196 issues

The LLM baseline is a comparison artifact only. It is not the deployed deterministic classifier. Its main failure mode is bug overprediction: the run predicted `bug` 70 times against 26 true bugs, and 30 true `question` issues were classified as `bug`.

## Final comparison table

| Model | Accuracy | Macro-F1 | Weighted-F1 | Bug F1 | Feature F1 | Docs F1 | Question F1 | Avg latency / issue | Cost / 196 issues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF + Logistic Regression | 0.7041 | 0.6681 | 0.7061 | 0.4444 | 0.7073 | 0.7692 | 0.7515 | 0.80 ms | local CPU only |
| RoBERTa-base | 0.7245 | 0.7116 | 0.7339 | 0.5556 | 0.6933 | 0.8571 | 0.7403 | 36.55 ms | local artifact |
| Claude Haiku 4.5 | 0.7041 | 0.7112 | 0.7294 | 0.5208 | 0.7692 | 0.8395 | 0.7153 | 1106.50 ms | $0.1118 |

## Deployment decision

- RoBERTa remains the selected primary classifier because it achieved the best overall combination of accuracy, macro-F1, bug F1, latency, and deterministic local deployment characteristics.
- The classical TF-IDF + Logistic Regression model remains useful as a fallback because it is much faster and easier to run in constrained environments.
- Claude Haiku is competitive on macro-F1, but it does not exceed RoBERTa, is much slower, incurs API cost, and shows a bug-overprediction error mode that is undesirable for the primary deterministic classifier.
- The LLM baseline remains useful for comparison and future generation-oriented workflows, not as the deployed deterministic issue classifier.

## Known weakness

The main remaining weakness is bug versus question confusion. That pattern is visible in both the deterministic and LLM runs, and it is especially pronounced in the Claude baseline, where many true question issues were classified as bug.
