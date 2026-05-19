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
13. Reranking and query rewriting remain next-step retrieval improvements and should be accepted only if their evaluation reports improve on the sparse and hybrid baselines.
14. The earlier 20,654-chunk RAG corpus count was from a pre-dedup docs import, not from the current corpus used by dense retrieval. The duplicate Node docs lived under a nested `api/api/...` path, which nearly doubled doc chunks from 7,074 to 14,148 while leaving resolved_issue chunks unchanged at 6,506. After deduplicating identical nested doc files during corpus discovery, the real corpus size is 13,580, and the embedding manifest matches that current corpus exactly.
