# Evals

## Classification golden set

The Week 7 classification golden set lives at `data/golden/classification_golden.jsonl`.

- It contains 25 manually selected, reviewable examples.
- It is meant to catch obvious regressions in the selected classifier.
- It is not the same thing as the full frozen `test.jsonl` metrics used during training evaluation.

## Eval gate

Run:

```bash
python evals/classification_eval.py
```

This script:

- loads the committed RoBERTa classifier artifacts through the same in-process service path used by `services/model-server`
- evaluates the classifier on the 25-example golden set
- computes accuracy, macro-F1, per-class F1, and the ordered confusion matrix
- writes `reports/eval_report.json`
- exits non-zero if any committed threshold is missed

Thresholds live in `evals/eval_thresholds.yaml`.

## Why CI should fail on regression

The golden set is small, so it is not a replacement for the full held-out test metrics. Its job is different:

- detect obvious label regressions on representative maintainer cases
- catch artifact or inference-path drift after service changes
- fail fast when the deployed classifier behavior meaningfully degrades

Because the gate is small and hand-curated, the thresholds are intentionally meaningful but not overly tight.

## RAG foundation

The Week 7 RAG foundation builds a reproducible local corpus from:

- Node.js project docs placed under `data/rag/raw/node_docs`
- held-out resolved Node.js issues from the validation, test, and excluded splits

Run:

```bash
python scripts/build_rag_corpus.py --smoke-query "How do I debug memory leak in https request?"
```

This writes:

- `data/rag/processed/rag_corpus.jsonl`
- `artifacts/rag/corpus_manifest.json`
- `artifacts/rag/retrieval_baseline_report.json`

The current chunking strategy is:

- markdown heading-aware chunking for docs, preserving section context
- structured issue records for resolved issues with title, problem/body, and an explicit limitation note that comments are not fetched yet

The first retrieval baseline is sparse TF-IDF. Dense retrieval now uses the local `sentence-transformers/all-MiniLM-L6-v2` model, chosen because it is small, fast on CPU, and a common semantic retrieval baseline. Hybrid retrieval combines normalized sparse and dense scores:

```text
hybrid_score = alpha * sparse_score + (1 - alpha) * dense_score
```

Current 25-example golden-set results:

| Retriever | alpha | hit@5 | hit@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| sparse TF-IDF | 1.00 | 0.5600 | 0.6000 | 0.3463 |
| dense MiniLM | 0.00 | 0.6000 | 0.6800 | 0.5584 |
| hybrid | 0.25 | 0.6400 | 0.7200 | 0.6040 |
| hybrid | 0.50 | 0.6800 | 0.7200 | 0.5647 |

Hybrid improves over sparse on this golden set. Alpha `0.50` has the best hit@5, while alpha `0.25` has the best MRR@10.

Still missing:

- reranker
- query rewrite
- generation evaluation

## RAG golden workflow

There are three working files in the RAG golden workflow:

- `data/rag/golden/rag_golden_candidates.jsonl`
- `data/rag/golden/rag_golden.draft.jsonl`
- `data/rag/golden/rag_golden.jsonl`

Candidates are generated from the real corpus and are explicitly marked with `needs_human_review=true`. They are not final evaluation data.

Generate candidates:

```bash
python scripts/make_rag_golden_candidates.py
```

Create the review report:

```bash
python scripts/review_rag_golden_candidates.py
```

Create an editable draft:

```bash
python scripts/create_rag_golden_draft.py
```

Validate candidates or drafts structurally:

```bash
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden_candidates.jsonl
```

The committed final file is `data/rag/golden/rag_golden.jsonl`. It is AI-assisted curated and validated, not a claim of deep manual human review. Final rows use `needs_human_review=false` with `human_review_status="ai_assisted_approved"` so this distinction is explicit. If a human reviewer later performs full manual review, use `human_review_status="approved"` for those rows.

```bash
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final
```

The final RAG golden set contains 25 `question` / `ideal_answer` / `ground_truth_chunk_ids` triples. It is retrieval evaluation data only; it is not a model-training set.

## Retrieval metrics

- `hit@5`: the fraction of questions where at least one correct chunk appears in the top 5 retrieved results.
- `MRR@10`: mean reciprocal rank over the top 10 results. Earlier correct hits count more than later ones.

Run retrieval eval only after the final file exists and passes validation:

```bash
python evals/rag_retrieval_eval.py --retriever sparse
python evals/rag_retrieval_eval.py --retriever dense
python evals/rag_retrieval_eval.py --retriever hybrid --alpha 0.5
```

Run the hybrid alpha sweep:

```bash
python scripts/sweep_rag_hybrid_alpha.py
```

Sparse TF-IDF remains the baseline to beat. Dense and hybrid retrieval currently beat it on the AI-assisted golden set; reranking and query rewrite should be measured against these committed reports rather than adopted by intuition.
