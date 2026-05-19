# RAG Golden Finalization Report

## Summary

- Total rows: 25
- Source distribution: 12 doc, 13 resolved_issue
- Final review status: `ai_assisted_approved`
- Review method: `strict_ai_assisted_finalization`

This set was AI-assisted curated and validated. It should be spot-checked before final submission.

## Rows Replaced

- `rag-golden-012`: replaced a broad API index page with a focused stream backpressure example backed by the `writable.write()` docs.
- `rag-golden-014`: replaced a TODO/XXX/FIXME inventory row with a concrete HTTPS `ECONNRESET` memory leak issue.
- `rag-golden-018`: replaced raw `cpplint` build output with a DNS lookup/threadpool blocking issue.
- `rag-golden-019`: replaced raw Ubuntu test-output noise with a zlib memory leak issue.
- `rag-golden-020`: replaced broad Node v6 planning notes with a specific `readFileSync()` versus `readFile()` buffer-size issue.
- `rag-golden-021`: replaced noisy Windows npm/TLS trace output with a focused `tls.createServer()` `secureOptions` documentation issue.
- `rag-golden-022`: replaced meeting agenda metadata with an HTTP response stream `readable` event issue.
- `rag-golden-025`: replaced changelog coordination content with a concrete HTTP CONNECT `CLOSE_WAIT` socket issue.

## Validation Result

```text
Rows: 25
Source distribution: {'doc': 12, 'resolved_issue': 13}
Needing review: 0
Approved: 25
Validation: PASS
```

## Retrieval Eval Result

```text
Examples: 25
hit@5: 0.5600
hit@10: 0.6000
MRR@10: 0.3463
Mean top score: 0.3806
Threshold gate: PASS
```

Per-source retrieval summary:

- doc: 12 examples, hit@5 0.4167, MRR@10 0.1451
- resolved_issue: 13 examples, hit@5 0.6923, MRR@10 0.5321

The sparse TF-IDF baseline passed the committed thresholds. Dense retrieval, hybrid retrieval, reranking, and query rewrite should be measured against this baseline rather than replacing it without evidence.
