# RAG Golden Codex Review V2 Summary

- Total rows reviewed: 25
- Rows replaced in v2: 8
- Rows still marked `replace_recommended`: 0
- Source distribution: {'doc': 12, 'resolved_issue': 13}

## Strongest examples

- `rag-golden-001`: How does `stream.pipeline()` clean up streams when a pipeline fails?
- `rag-golden-005`: What do the `fs.readFile()` docs recommend when I want to avoid buffering an entire file in memory?
- `rag-golden-014`: What resolved Node.js issue reports a memory leak when `https.request()` hits `ECONNRESET`?
- `rag-golden-018`: What resolved issue describes `dns.lookup()` blocking other filesystem or serial I/O?
- `rag-golden-023`: What resolved issue discusses FIPS test failures and API problems in Node.js crypto?

## Weakest examples still worth human attention

- `rag-golden-003`: What does `response.write()` do on an `http.ServerResponse`?
- `rag-golden-007`: How does `response.write()` behave on an `Http2ServerResponse`?
- `rag-golden-009`: Where do the HTTPS docs show how to call `https.request()`?
- `rag-golden-011`: What does the Node.js Permission Model restrict?
- `rag-golden-024`: Which resolved issue tracks adding version and deprecation history to API docs?

## Next manual steps

1. Start from `data/rag/golden/rag_golden.codex_reviewed_v2.jsonl` rather than the previous draft.
2. Spot-check every rewritten row against its referenced chunk in `reports/rag_golden_review.md` or the corpus itself.
3. Tighten any remaining doc answers that still read too much like API signatures instead of short explanations.
4. If a human reviewer agrees a row is final, copy it into `data/rag/golden/rag_golden.jsonl`, keep the chunk ids unchanged, set `needs_human_review` to `false`, and set `human_review_status` to `approved`.
5. Run `python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final` before any retrieval eval.
6. Only then run `python evals/rag_retrieval_eval.py`.
