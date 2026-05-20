# Architectural Decisions

1. The API service is split into transport, service, repository, domain, and infra layers to keep external dependencies out of routers.
2. Vault reachability is checked during API startup so missing secret infrastructure fails early instead of surfacing later as partial runtime errors.
3. Structured logging is implemented with request and trace correlation fields plus centralized redaction before emission.
4. Placeholder model-server outputs are deterministic so downstream integration can start before classifier artifacts exist.
5. Widget configuration is modeled in SQL from day one because embedding policy and theming are operational data, not frontend constants.
6. The auth foundation uses a minimal in-house JWT and password hashing layer for now instead of `fastapi-users`. This kept churn and new dependencies low in the Week 7 skeleton while preserving clean service and repository boundaries. A future compatibility step is to evaluate replacing or wrapping this with `fastapi-users` once the persistence and user lifecycle surface stabilizes.
7. JWT secrets are currently loaded from the API config/environment path for local development and tests. Wiring the signing key to a concrete Vault secret path remains a follow-up once Vault paths and policies are defined.
8. The initial RAG corpus is built from held-out resolved issues plus optional local Node.js docs, not from the classifier training split. This keeps retrieval examples closer to real support and maintainer history while reducing leakage from the supervised classifier training set.
9. The Week 7 retrieval baseline started as sparse TF-IDF over structured, section-aware chunks so there was a simple local baseline to beat.
10. Dense retrieval uses `sentence-transformers/all-MiniLM-L6-v2` because it is small, local, CPU-friendly, and a common semantic retrieval baseline. The embedding index is generated under `artifacts/rag/embeddings/`.
11. Hybrid retrieval linearly combines per-query normalized sparse and dense scores. Against the current 25-example AI-assisted RAG golden set, sparse reaches hit@5 0.56 and MRR@10 0.3463; dense reaches hit@5 0.60 and MRR@10 0.5584; hybrid alpha 0.50 reaches the best hit@5 at 0.68, while hybrid alpha 0.25 reaches the best MRR@10 at 0.6040.
12. The RAG golden set is AI-assisted curated and validated, not a claim of deep manual human review. Dense, hybrid, and reranked retrieval must beat the sparse TF-IDF baseline against that set rather than replacing it by intuition.
13. Reranking is implemented as a local cross-encoder pass over retrieved candidates, using `cross-encoder/ms-marco-MiniLM-L-6-v2` in offline-only mode from the local path `artifacts/rag/reranker_model`. The service now prefers reranked retrieval when that path exists and falls back to hybrid with an explicit diagnostic if the local reranker model is missing or unavailable.
15. The earlier 20,654-chunk RAG corpus count was from a pre-dedup docs import, not from the current corpus used by dense retrieval. The duplicate Node docs lived under a nested `api/api/...` path, which nearly doubled doc chunks from 7,074 to 14,148 while leaving resolved_issue chunks unchanged at 6,506. After deduplicating identical nested doc files during corpus discovery, the real corpus size is 13,580, and the embedding manifest matches that current corpus exactly.
16. RAG query rewrite is deterministic and offline. It expands common Node.js terms and predicts a preferred source type, but it does not call Claude or any external API.
17. Metadata-aware boosting is a small explainable ranking adjustment after retrieval, not a default hard filter. Explicit `source_type` filtering is available for docs-only or resolved-issue-only queries.
18. The measured 25-example RAG retrieval results are:

| Retriever | Alpha | Rewrite+Boost | Rerank Top N | hit@5 | hit@10 | MRR@10 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| sparse TF-IDF | 1.00 | no | - | 0.5600 | 0.6000 | 0.3463 |
| dense MiniLM | 0.00 | no | - | 0.6000 | 0.6800 | 0.5584 |
| hybrid | 0.50 | yes | - | 0.7600 | 0.8000 | 0.6080 |
| reranked hybrid | 0.50 | no | 20 | 0.7200 | 0.7200 | 0.6280 |
| reranked hybrid | 0.50 | yes | 20 | 0.8000 | 0.8000 | 0.6280 |
| reranked hybrid, MRR-optimized sweep | 0.25 | no | 10 | 0.7200 | 0.7200 | 0.6533 |

19. The selected default RAG pipeline is reranked hybrid retrieval plus deterministic query rewrite and metadata boost with `alpha=0.50` and `rerank_top_n=20`. This is the best default for the current `/rag/answer` endpoint because it raises hit@5 to `0.8000` while still improving MRR@10 over the non-reranked hybrid baseline.
20. The MRR-optimized variant is reranked hybrid with `alpha=0.25` and `rerank_top_n=10`, which reaches MRR@10 `0.6533` but lowers hit@5 to `0.7200`. Because the current RAG answer path uses multiple retrieved chunks, hit@5 is the better default optimization target than MRR alone.
21. `/chat` uses a single Claude tool-calling LLM when enabled, not a multi-agent workflow. The deterministic router is the fallback for dev, tests, and Claude outages.
22. Long-term memory is explicit-only through `write_memory`; short-term memory is redacted and TTL-bound. In-memory short-term memory is restricted to dev/test via `API_ALLOW_IN_MEMORY_MEMORY=true`.
