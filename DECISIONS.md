# Architectural Decisions

1. The API service is split into transport, service, repository, domain, and infra layers to keep external dependencies out of routers.
2. Vault reachability is checked during API startup so missing secret infrastructure fails early instead of surfacing later as partial runtime errors.
3. Structured logging is implemented with request and trace correlation fields plus centralized redaction before emission.
4. Placeholder model-server outputs are deterministic so downstream integration can start before classifier artifacts exist.
5. Widget configuration is modeled in SQL from day one because embedding policy and theming are operational data, not frontend constants.
6. **Auth: dual-layer strategy — custom invite-flow routes at `/auth` plus fastapi-users at `/auth/v2`.** The custom scrypt + HS256 layer handles registration, login, `/me`, and the invite flow (which fastapi-users has no built-in concept for). fastapi-users v13 is wired up alongside it at `/auth/v2` and `/users/v2` via a `SyncUserDatabase` adapter that bridges the sync SQLAlchemy Core repository to fastapi-users' async interface using `asyncio.to_thread`. This preserves the invite routes and all existing tests while delivering the fastapi-users auth, reset-password, verify, and user-management surface. The `users` table gained `is_superuser` and `is_verified` columns (migration `0004`) to satisfy the fastapi-users user protocol.
7. JWT secrets still allow local config/environment fallback for development and tests, but deployed startup now supports a concrete Vault secret path for the signing key and fails early when `API_REQUIRE_VAULT=true` and the required secret cannot be resolved.
8. The initial RAG corpus is built from held-out resolved issues plus optional local Node.js docs, not from the classifier training split. This keeps retrieval examples closer to real support and maintainer history while reducing leakage from the supervised classifier training set.
9. The Week 7 retrieval baseline started as sparse TF-IDF over structured, section-aware chunks so there was a simple local baseline to beat.
10. Dense retrieval uses `sentence-transformers/all-MiniLM-L6-v2` because it is small, local, CPU-friendly, and a common semantic retrieval baseline. The embedding index is generated under `artifacts/rag/embeddings/`.
11. Hybrid retrieval linearly combines per-query normalized sparse and dense scores. Against the current 25-example AI-assisted RAG golden set, sparse reaches hit@5 0.56 and MRR@10 0.3463; dense reaches hit@5 0.60 and MRR@10 0.5584; hybrid alpha 0.50 reaches the best hit@5 at 0.68, while hybrid alpha 0.25 reaches the best MRR@10 at 0.6040.
12. The RAG golden set is AI-assisted curated and validated, not a claim of deep manual human review. Dense, hybrid, and reranked retrieval must beat the sparse TF-IDF baseline against that set rather than replacing it by intuition.
13. Reranking is implemented as a local cross-encoder pass over retrieved candidates, using `cross-encoder/ms-marco-MiniLM-L-6-v2` in offline-only mode from the local path `artifacts/rag/reranker_model`. The service now prefers reranked retrieval when that path exists and falls back to hybrid with an explicit diagnostic if the local reranker model is missing or unavailable.
14. The earlier 20,654-chunk RAG corpus count was from a pre-dedup docs import, not from the current corpus used by dense retrieval. The duplicate Node docs lived under a nested `api/api/...` path, which nearly doubled doc chunks from 7,074 to 14,148 while leaving resolved_issue chunks unchanged at 6,506. After deduplicating identical nested doc files during corpus discovery, the real corpus size is 13,580, and the embedding manifest matches that current corpus exactly.
15. RAG query rewrite is deterministic and offline. It expands common Node.js terms and predicts a preferred source type, but it does not call Claude or any external API.
16. Metadata-aware boosting is a small explainable ranking adjustment after retrieval, not a default hard filter. Explicit `source_type` filtering is available for docs-only or resolved-issue-only queries.
17. The measured 25-example RAG retrieval results are:

| Retriever | Alpha | Rewrite+Boost | Rerank Top N | hit@5 | hit@10 | MRR@10 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| sparse TF-IDF | 1.00 | no | - | 0.5600 | 0.6000 | 0.3463 |
| dense MiniLM | 0.00 | no | - | 0.6000 | 0.6800 | 0.5584 |
| hybrid | 0.50 | yes | - | 0.7600 | 0.8000 | 0.6080 |
| reranked hybrid | 0.50 | no | 20 | 0.7200 | 0.7200 | 0.6280 |
| reranked hybrid | 0.50 | yes | 20 | 0.8000 | 0.8000 | 0.6280 |
| reranked hybrid, MRR-optimized sweep | 0.25 | no | 10 | 0.7200 | 0.7200 | 0.6533 |

18. The selected default RAG pipeline is reranked hybrid retrieval plus deterministic query rewrite and metadata boost with `alpha=0.50` and `rerank_top_n=20`. This is the best default for the current `/rag/answer` endpoint because it raises hit@5 to `0.8000` while still improving MRR@10 over the non-reranked hybrid baseline.
19. The MRR-optimized variant is reranked hybrid with `alpha=0.25` and `rerank_top_n=10`, which reaches MRR@10 `0.6533` but lowers hit@5 to `0.7200`. Because the current RAG answer path uses multiple retrieved chunks, hit@5 is the better default optimization target than MRR alone.
20. `/chat` uses a single Claude tool-calling LLM as the primary runtime path when enabled, not a multi-agent workflow. The deterministic router remains the reproducible fallback for explicit `use_llm=false` requests, tests, CI, and Claude outages.
21. Long-term memory is explicit-only through `write_memory`; short-term memory is redacted and TTL-bound. In-memory short-term memory is restricted to dev/test via `API_ALLOW_IN_MEMORY_MEMORY=true`.
22. The Streamlit service is an internal/admin API client, not another backend implementation. It calls FastAPI for chat, widget admin, memory views, reports, and recent events so the React widget and API paths remain the protected integration surface.
23. RAG generation evaluation is a deterministic offline regression gate over the extractive `/rag/answer` path. It uses frozen judge version `frozen-rag-judge-v1` and does not call Claude. Initial generation labels remain `ai_assisted_initial` until manually spot-checked.
24. **Tracing backend: Jaeger via OpenTelemetry SDK (OTLP gRPC).** Jaeger was chosen because it runs as a single Docker image with no external dependencies, ships a built-in UI for trace tree exploration, and accepts the standard OTLP protocol so the instrumentation is backend-agnostic. Every LLM call (`llm.select_tool`, `llm.final_response`), tool execution (`tool.<name>`), and RAG retrieval (`rag.retrieve`) is a span. Span attributes include model name, token counts (input/output), selected tool name, retriever type, and citation count. The OTLP exporter endpoint is configured via `API_OTEL_EXPORTER_ENDPOINT` (default: `http://jaeger:4317`). When the endpoint is absent, spans are emitted to the console only. `API_REQUIRE_TRACING=true` will fail startup if the OTLP endpoint is missing.
25. Long-term memory is now pgvector-capable episodic memory with local MiniLM embeddings at dimension 384 when the embedding model is cached locally and Postgres `vector` support is available. PostgreSQL deployments now attempt an HNSW cosine index for `memories.embedding`, falling back to IVFFlat where HNSW support is unavailable. The service still permits explicit text-only fallback in dev/test when configured, and production tuning remains future work.
26. Widget embedding policy is enforced at the public widget loader/config surface using configured `allowed_origins`, `Origin` or `Referer` headers when present, and a `Content-Security-Policy: frame-ancestors ...` response header. The localhost demo path remains explicitly opt-in through `API_ENABLE_DEMO_WIDGET_FALLBACK=true`.
27. Classification golden evaluation now supports the selected transformer, the classical baseline, and the frozen LLM baseline predictions. The 25-example golden gate is a regression signal, not the primary model-selection metric, and a model may legitimately fail the golden thresholds even when it remains useful as a comparison baseline.
28. The default RAG issue corpus still uses resolved issue title/body records. Optional sample ingestion for issue comments is now supported through a separate fetch script and comment chunk type, but it is not required for evals or CI and does not claim full historical maintainer-comment coverage.
29. The production widget path is still documented rather than fully collapsed into a single bundled delivery artifact. The current shipped demo uses the widget service for clarity, while production proof comes from built `services/widget/dist` assets and `reports/widget_bundle_report.json`.
32. Redis fixed-window rate limiting is implemented for project/demo scope, with separate global, chat, and widget-public-surface limits plus configurable fail-open behavior. Threshold tuning and abuse-policy hardening remain future work.
30. **Embedding model comparison (25-example golden set, dense-only retrieval, 13,580-chunk corpus).** `all-MiniLM-L12-v2` (12 layers, 384-dim, ~120 MB) was benchmarked against the current `all-MiniLM-L6-v2` (6 layers, 384-dim, ~80 MB). Results:

| Model | hit@5 | hit@10 | MRR@10 | Build time (CPU) |
|---|---:|---:|---:|---:|
| all-MiniLM-L6-v2 (current) | 0.6000 | 0.6800 | 0.5584 | ~64 s |
| all-MiniLM-L12-v2 | **0.7200** | **0.7200** | **0.6133** | ~405 s |

The 12-layer model improves hit@5 by +12 pp and MRR@10 by +0.055 for dense-only retrieval at the cost of 6× longer index build time. However, the current default pipeline (`all-MiniLM-L6-v2` + hybrid alpha=0.50 + rerank top-20) already achieves hit@5=0.80, which exceeds the L12-v2 dense-only result. Upgrading the dense base to L12-v2 is deferred until a full hybrid+rerank sweep with L12-v2 confirms a net gain over the existing pipeline. Full report in `reports/embedding_comparison_report.json`.

31. **Three-way classifier comparison (196-example test set, `nodejs/node`).** The three models evaluated are the fine-tuned RoBERTa-base transformer, a classical TF-IDF + Logistic Regression baseline, and a frozen Claude Haiku-4-5 LLM baseline. Full numbers in `artifacts/classifier/comparison/model_comparison.md`; summary:

| Model | Accuracy | Macro-F1 | Bug F1 | Avg latency | Cost |
|---|---:|---:|---:|---:|---:|
| classical TF-IDF + LogReg | 0.7041 | 0.6681 | 0.4444 | 0.80 ms | local CPU only |
| **RoBERTa-base (selected)** | **0.7245** | **0.7116** | **0.5556** | 36.55 ms | local artifact |
| Claude Haiku-4-5 LLM | 0.7041 | 0.7112 | 0.5208 | 1106.50 ms | $0.1118 / 196 |

RoBERTa wins on accuracy, macro-F1, and bug F1, with a 36 ms local latency and zero inference cost. Claude Haiku reaches nearly the same macro-F1 (0.7112 vs 0.7116) but at 30× the latency and per-call API cost, making it unsuitable as the primary classifier. Its dominant error mode is bug overprediction (70 predicted bugs vs 26 true bugs; 30 true questions misclassified as bugs). The classical model is retained as a fast fallback — 45× faster than RoBERTa — but trails both neural models on macro-F1 and bug detection.
