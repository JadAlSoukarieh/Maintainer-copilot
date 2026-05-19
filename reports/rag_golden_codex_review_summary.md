# RAG Golden Codex Review Summary

- Total rows reviewed: 25
- Rows rewritten: 25
- Rows marked `replace_recommended`: 8
- Source distribution: {'doc': 12, 'resolved_issue': 13}

## Strongest examples

- `rag-golden-001`: How does `stream.pipeline()` clean up streams when a pipeline fails? — Specific stream cleanup behavior with a focused chunk.
- `rag-golden-002`: Where do the Node.js DNS docs list resolver error codes such as `dns.NODATA` and `dns.TIMEOUT`? — Clear DNS docs lookup with a concise grounded answer.
- `rag-golden-005`: What do the `fs.readFile()` docs recommend when I want to avoid buffering an entire file in memory? — Practical fs guidance about memory usage and streaming.
- `rag-golden-013`: What resolved issue describes recurring `ECONNRESET` errors on Node 6 HTTP and HTTPS servers? — Real operational ECONNRESET issue with concrete context.
- `rag-golden-023`: What resolved issue discusses FIPS test failures and API problems in Node.js crypto? — Strong crypto/FIPS issue with clear problem framing.

## Weakest examples

- `rag-golden-012`: Where is the main index for the Node.js API docs? — API index page is too broad to be a strong retrieval target.
- `rag-golden-018`: Which resolved issue captured `cpplint` and `header_guard` failures during `make test`? — Mostly raw build log output.
- `rag-golden-019`: Which resolved issue collected failing test output under Ubuntu 14.04? — Mostly raw failing test output.
- `rag-golden-021`: Which resolved issue captured Windows `npm install` failures with TLS stack traces? — Mostly TLS/npm stack traces and warnings.
- `rag-golden-022`: Which issue contains the Node.js Foundation CTC meeting agenda for 2016-08-10? — Meeting agenda metadata rather than a support question.

## Next manual steps

1. Open `reports/rag_golden_review.md` and `data/rag/golden/rag_golden.codex_reviewed.jsonl` side by side.
2. Start with all rows marked `replace_recommended: true` and either rewrite them more aggressively or replace them with better corpus-backed examples.
3. For the remaining rows, verify that each answer is fully supported by the referenced chunk and trim any wording that still feels auto-generated.
4. When a row is genuinely approved by a human, copy it into `data/rag/golden/rag_golden.jsonl`, set `needs_human_review` to `false`, and set `human_review_status` to `approved`.
5. Run `python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final` before any retrieval evaluation.
6. Only after the final reviewed file passes validation should you run `python evals/rag_retrieval_eval.py`.
