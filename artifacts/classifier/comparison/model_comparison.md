# Model Comparison

## Dataset

Repository: `nodejs/node`  
Data hash: `db3e1d356b3202533fc16fe75a21fdf40c9a5c060a19172ec3d403398f7c6d27`  
Test examples: 196

## Results

| Model | Accuracy | Macro-F1 | Weighted-F1 | Bug F1 | Feature F1 | Docs F1 | Question F1 | Avg latency / issue | Cost / 196 issues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| classical_tfidf_logreg | 0.7041 | 0.6681 | 0.7061 | 0.4444 | 0.7073 | 0.7692 | 0.7515 | 0.80 ms | local CPU only |
| transformer_roberta_base | 0.7245 | 0.7116 | 0.7339 | 0.5556 | 0.6933 | 0.8571 | 0.7403 | 36.55 ms | local GPU/CPU artifact |
| llm_claude_haiku_4_5 | 0.7041 | 0.7112 | 0.7294 | 0.5208 | 0.7692 | 0.8395 | 0.7153 | 1106.50 ms | $0.1118 |


## Decision

RoBERTa-base remains the selected primary classifier. Claude Haiku came very close on macro-F1, but RoBERTa still has the best overall combination of accuracy, macro-F1, bug F1, latency, and deterministic local deployment characteristics.

The LLM baseline is retained as a comparison artifact, not as the deployed deterministic classifier. Its main error mode is bug overprediction: it predicted `bug` 70 times against 26 true bugs, and 30 true `question` issues were classified as `bug`.

The classical model remains useful as a fast fallback. It is much lower latency than either RoBERTa or Claude Haiku, but it trails both on macro-F1 and bug detection.
