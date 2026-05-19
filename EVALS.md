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

The current retrieval baseline is sparse TF-IDF only. It exists to create a measurable baseline for later improvements.

Still missing:

- dense embeddings
- hybrid retrieval
- reranker
- query rewrite
- a filled 25-example RAG golden set
- generation evaluation

## RAG golden workflow

There are two RAG golden files:

- `data/rag/golden/rag_golden_candidates.jsonl`
- `data/rag/golden/rag_golden.jsonl`

Candidates are generated from the real corpus and are explicitly marked with `needs_human_review=true`. They are not final evaluation data.

Generate candidates:

```bash
python scripts/make_rag_golden_candidates.py
```

Validate candidates:

```bash
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden_candidates.jsonl
```

After manual review, copy and edit:

```bash
cp data/rag/golden/rag_golden_candidates.jsonl data/rag/golden/rag_golden.jsonl
```

Then set `needs_human_review=false` on all 25 reviewed rows and validate the final file:

```bash
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final
```

The final project needs 25 reviewed `question` / `ideal_answer` / `ground_truth_chunk_ids` triples.

## Retrieval metrics

- `hit@5`: the fraction of questions where at least one correct chunk appears in the top 5 retrieved results.
- `MRR@10`: mean reciprocal rank over the top 10 results. Earlier correct hits count more than later ones.

Run retrieval eval only after the reviewed final file exists:

```bash
python evals/rag_retrieval_eval.py
```

The sparse TF-IDF retriever is the current baseline to beat later with dense retrieval, hybrid retrieval, and reranking.
