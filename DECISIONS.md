# Architectural Decisions

1. The API service is split into transport, service, repository, domain, and infra layers to keep external dependencies out of routers.
2. Vault reachability is checked during API startup so missing secret infrastructure fails early instead of surfacing later as partial runtime errors.
3. Structured logging is implemented with request and trace correlation fields plus centralized redaction before emission.
4. Placeholder model-server outputs are deterministic so downstream integration can start before classifier artifacts exist.
5. Widget configuration is modeled in SQL from day one because embedding policy and theming are operational data, not frontend constants.
6. The auth foundation uses a minimal in-house JWT and password hashing layer for now instead of `fastapi-users`. This kept churn and new dependencies low in the Week 7 skeleton while preserving clean service and repository boundaries. A future compatibility step is to evaluate replacing or wrapping this with `fastapi-users` once the persistence and user lifecycle surface stabilizes.
7. JWT secrets are currently loaded from the API config/environment path for local development and tests. Wiring the signing key to a concrete Vault secret path remains a follow-up once Vault paths and policies are defined.
8. The initial RAG corpus is built from held-out resolved issues plus optional local Node.js docs, not from the classifier training split. This keeps retrieval examples closer to real support and maintainer history while reducing leakage from the supervised classifier training set.
9. The Week 7 retrieval baseline is sparse TF-IDF over structured, section-aware chunks. Dense embeddings, hybrid retrieval, reranking, and query rewriting are deferred so there is a simple local baseline to beat later.
10. The RAG golden set is generated as candidate data first and must be manually reviewed before it is treated as final evaluation input. Dense, hybrid, and reranked retrieval must beat the sparse TF-IDF baseline against that reviewed set rather than replacing it by intuition.
