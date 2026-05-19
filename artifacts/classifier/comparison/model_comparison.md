# Model Comparison

## Dataset

Repository: `nodejs/node`  
Data hash: `db3e1d356b3202533fc16fe75a21fdf40c9a5c060a19172ec3d403398f7c6d27`  
Test examples: 196

## Results

| Model | Accuracy | Macro-F1 | Weighted-F1 | Bug F1 | Feature F1 | Docs F1 | Question F1 | Avg latency / issue |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| classical_tfidf_logreg | 0.7041 | 0.6681 | 0.7061 | 0.4444 | 0.7073 | 0.7692 | 0.7515 | 0.80 ms |
| transformer_roberta_base | 0.7245 | 0.7116 | 0.7339 | 0.5556 | 0.6933 | 0.8571 | 0.7403 | 36.55 ms |


## Decision

RoBERTa-base is selected as the final transformer model because it achieved the best test macro-F1 and improved the weakest class, bug, compared with the classical baseline.

The classical model remains useful as a fast baseline. It is much lower latency, but RoBERTa gives better macro-F1 and better bug detection.
