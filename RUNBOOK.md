# Runbook

## Local bootstrap

1. Create and activate the repo-local virtual environment:
   `python3 -m venv .venv`
   `source .venv/bin/activate`
2. Bootstrap Python dependencies:
   `python scripts/bootstrap_dev.py`
3. Copy `.env.example` to `.env` when you need local environment variables.
4. For local tests and non-Docker runs, set:
   `API_REQUIRE_VAULT=false`
   `API_JWT_SECRET=dev-only-jwt-secret-change-me`
   `API_REQUIRE_LLM_KEY=false`
   `API_CHAT_LLM_ENABLED=true`
   `API_CHAT_ALLOW_ENV_KEY_FALLBACK=true`
   `API_ALLOW_IN_MEMORY_MEMORY=true`

## Brief compliance status

Completed:

- classifier comparison and artifact-backed model-server inference
- advanced RAG retrieval, reranking, and deterministic generation eval
- `/chat` orchestration, React widget demo, Streamlit internal console, Docker stack, and CI

Partial / honest deviations:

- auth still uses the custom invite/JWT flow as the primary application path, even though `fastapi-users` routes are present at `/auth/v2` and `/users/v2`
- observability is OTEL/Jaeger plus recent-events/request IDs for project/demo scope, not a full production tracing program
- resolved issue title/body is still the default corpus input; optional issue-comment sample ingestion exists, but full historical coverage is not implemented
- long-term memory now has a pgvector ANN index path, but production tuning and large-scale validation are still limited
- the demo still serves the widget through the widget service instead of a single API-hosted production bundle

## Local runs

- API:
  `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
- Model server:
  `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
- Streamlit internal console:
  `cd services/chatbot && streamlit run app.py --server.address=0.0.0.0 --server.port=8501`
- Tests:
  `./.venv/bin/python scripts/run_tests.py`

## Streamlit internal console

URL: `http://localhost:8501`

Streamlit is the internal/admin surface. It calls FastAPI only and does not duplicate classifier, RAG, or model-server logic. The React widget remains the embedded production-shaped surface.

Tabs:

- Chat: `/chat` with issue context, Claude tool-calling as the primary runtime mode when enabled, deterministic fallback as the backup path, citations, request ID, and trace ID.
- Issue Tools: classify, entity extraction, summarization, and RAG through `/chat`.
- Widget Admin: list/create/update/disable widgets and render embed snippets.
- Evals / Metrics: `/reports/summary` metric cards and raw report details.
- Memory Inspector: redacted short-term events plus pgvector-capable episodic long-term memories, with explicit vector/text fallback diagnostics.
- Logs / Observability: lightweight recent events/request IDs. This is not a full tracing backend.

Local demo flags:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_ALLOW_IN_MEMORY_MEMORY=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
```

Production should keep auth enabled, use Redis for short-term memory, keep demo widget fallback disabled, resolve secrets through Vault, and disable text-only long-term memory fallback unless explicitly intended.

Model-server smoke request:

```bash
curl -X POST http://localhost:8001/classify \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "dns.lookup blocks filesystem I/O",
    "body": "On networks with slow DNS response, blocking calls from dns.lookup delay serial and filesystem work."
  }'
```

Golden classifier eval:

```bash
python evals/classification_eval.py
python evals/classification_eval.py --model all --gate primary
```

`--model all --gate primary` checks the 25-example classification golden set across the selected transformer, the classical baseline, and frozen LLM baseline predictions when those artifacts exist. Only the deployed selected transformer blocks by default; classical and LLM baseline failures are reported as warnings unless `--gate all` or `--strict-baselines` is used. The golden set is a regression gate, not the main model-selection metric.

Dev-only MLflow training run logging:

```bash
python scripts/log_training_run.py
mlflow ui --backend-store-uri mlruns --port 5000
```

This logs existing frozen classifier metrics, training args, and the comparison report to local `mlruns/`. MLflow is installed from top-level `requirements-dev.txt` for development/review only; do not add it to API runtime requirements or production images.

RAG corpus build and sparse retrieval smoke check:

```bash
python scripts/build_rag_corpus.py \
  --issues-path data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl \
  --docs-dir data/rag/raw/node_docs \
  --out data/rag/processed/rag_corpus.jsonl \
  --smoke-query "How do I debug memory leak in https request?"
```

Optional issue-comment sample ingestion:

```bash
python scripts/fetch_rag_issue_comments.py --only-golden --limit 25
python scripts/build_rag_corpus.py
```

If `data/rag/raw/issue_comments_sample.jsonl` exists, the corpus builder adds `issue_comment` rows. If it is missing, the default resolved-issue title/body corpus remains unchanged.

NER smoke request:

```bash
curl -X POST http://localhost:8001/ner \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "fs.utimes fails on v6.5.0",
    "body": "See /usr/local/lib/node_modules/app/index.js and https://nodejs.org/docs. Call crypto.pbkdf2() with --trace-warnings."
  }'
```

Summarizer smoke request:

```bash
curl -X POST http://localhost:8001/summarize \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Memory leak in https.request",
    "body": "Version: v6.8.0. Platform: Ubuntu 16.04. Repro: send many requests. Actual: memory grows after ECONNRESET.",
    "max_bullets": 3
  }'
```

`/ner` is rule-based and `/summarize` is extractive for now. Both are integration tools for the chatbot pipeline, not external LLM-backed features.

The RAG corpus builder currently ingests held-out issues from `data/processed/val.jsonl`, `data/processed/test.jsonl`, and `data/processed/excluded_issues.jsonl`, plus any local docs placed in `data/rag/raw/node_docs`. Retrieval supports sparse TF-IDF, local MiniLM dense embeddings, hybrid sparse+dense ranking, deterministic query rewrite, metadata-aware boosting, optional source filtering, and an optional local cross-encoder reranker.

Current limitation: resolved issue chunks still use issue title/body only. Maintainer comments and closing answers are not yet ingested into the corpus.

To prepare local Node docs:

```bash
git clone --depth 1 https://github.com/nodejs/node.git /tmp/node
mkdir -p data/rag/raw/node_docs
cp -r /tmp/node/doc/api data/rag/raw/node_docs/api
```

Rebuild the corpus after copying docs:

```bash
python scripts/build_rag_corpus.py \
  --issues-path data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl \
  --docs-dir data/rag/raw/node_docs \
  --out data/rag/processed/rag_corpus.jsonl \
  --smoke-query "How do I debug memory leak in https request?"
```

Docs are required before advanced RAG eval and doc-grounded retrieval comparison.

RAG golden workflow:

```bash
python scripts/make_rag_golden_candidates.py
python scripts/review_rag_golden_candidates.py
python scripts/create_rag_golden_draft.py
# candidates are not final eval data
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final
python evals/rag_retrieval_eval.py
```

The current final RAG golden set is AI-assisted curated and validated with `human_review_status=ai_assisted_approved`; it should be spot-checked before submission. Sparse TF-IDF is the baseline to beat, and sparse, dense, hybrid, and reranked retrieval have all been measured against it.

Dense and hybrid retrieval workflow:

```bash
python scripts/build_rag_embeddings.py
python evals/rag_retrieval_eval.py --retriever sparse
python evals/rag_retrieval_eval.py --retriever dense
python evals/rag_retrieval_eval.py --retriever hybrid --alpha 0.5
python evals/rag_retrieval_eval.py --retriever hybrid --alpha 0.5 --query-rewrite --metadata-boost --report-path reports/rag_eval_hybrid_rewrite_boost.json
python scripts/sweep_rag_hybrid_alpha.py
python evals/rag_retrieval_eval.py --retriever reranked --base-retriever hybrid --alpha 0.5 --rerank-top-n 20 --reranker-model artifacts/rag/reranker_model --query-rewrite --metadata-boost --report-path reports/rag_eval_reranked.json
python scripts/sweep_rag_reranker.py --reranker-model artifacts/rag/reranker_model
```

The embedding builder uses the local `sentence-transformers/all-MiniLM-L6-v2` model cache. It does not call an external embedding API. The reranker runs locally from `artifacts/rag/reranker_model`. If that path is missing, the API falls back to hybrid plus rewrite and boost and reports the fallback in RAG diagnostics instead of crashing the local demo.

Current RAG retrieval results:

| Retriever | Alpha | Rewrite+Boost | Rerank Top N | hit@5 | hit@10 | MRR@10 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| sparse TF-IDF | 1.00 | no | - | 0.5600 | 0.6000 | 0.3463 |
| dense MiniLM | 0.00 | no | - | 0.6000 | 0.6800 | 0.5584 |
| hybrid | 0.50 | yes | - | 0.7600 | 0.8000 | 0.6080 |
| reranked hybrid | 0.50 | no | 20 | 0.7200 | 0.7200 | 0.6280 |
| reranked hybrid | 0.50 | yes | 20 | 0.8000 | 0.8000 | 0.6280 |
| reranked hybrid, MRR-optimized sweep | 0.25 | no | 10 | 0.7200 | 0.7200 | 0.6533 |

The selected default is reranked hybrid plus deterministic query rewrite and metadata boost with `alpha=0.50` and `rerank_top_n=20`. The MRR-optimized variant is `alpha=0.25` with `rerank_top_n=10`, but it gives up hit@5. Because `/rag/answer` uses multiple returned chunks, hit@5 is the better default optimization target.

API RAG answer smoke request:

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "How do I debug a memory leak in https request?",
    "top_k": 5,
    "retriever": "reranked",
    "alpha": 0.5,
    "query_rewrite": true,
    "metadata_boost": true
  }'
```

`/rag/answer` is an extractive fallback over retrieved Node.js docs/issues. It returns citations, rewritten query, intent, and diagnostics for future chatbot tool use. It does not call Claude or external APIs. Optional `source_type` can restrict retrieval to `doc` or `resolved_issue`; otherwise metadata boost is only a small ranking signal. When the local reranker model exists, the API prefers reranked retrieval. Otherwise it falls back to hybrid plus rewrite and boost and exposes the fallback in diagnostics. Production chatbot RAG should require authenticated user access.

RAG generation eval is deterministic and offline:

```bash
python evals/rag_generation_eval.py
```

It writes `reports/rag_generation_eval_report.json` with frozen judge version `frozen-rag-judge-v1`. It evaluates the current extractive RAG answer path, not Claude. Initial labels in `data/rag/golden/rag_generation_human_labels.jsonl` are marked `ai_assisted_initial`; change them to `human_spot_checked` only after real manual spot-checking.

Manual review helper for the five labeled examples:

```bash
python scripts/review_rag_generation_labels.py
```

That writes `reports/rag_generation_human_review.md`. Review the markdown, edit `data/rag/golden/rag_generation_human_labels.jsonl` manually, and then rerun `python evals/rag_generation_eval.py`.

Optional manual Claude generation check:

```bash
python evals/rag_generation_eval.py --mode claude --limit 5 --output reports/rag_generation_eval_report_claude_5.json
```

Claude mode is manual/local only for live smoke and quality checks. CI keeps deterministic mode as the required regression gate even though runtime/demo mode is Claude-first when enabled.

## Final backend smoke

Deterministic smoke against a running stack:

```bash
python scripts/final_backend_smoke.py --mode fallback
```

The smoke checks API/model-server health, widget origin/CSP behavior, deterministic RAG chat, classify chat, explicit memory write, memory search, report summary, and recent events. It writes `reports/final_backend_smoke_report.json` with secret-like values redacted.

For one controlled live Claude smoke, keep `.env.local` ignored and load it locally before starting the API:

```bash
set -a
source .env.local
set +a
API_REQUIRE_VAULT=false \
API_AUTH_OPTIONAL_FOR_DEV=true \
API_CHAT_LLM_ENABLED=true \
API_CHAT_ALLOW_ENV_KEY_FALLBACK=true \
API_ENABLE_DEMO_WIDGET_FALLBACK=true \
API_ALLOW_IN_MEMORY_MEMORY=true \
docker compose --env-file .env.example up -d
```

Then run:

```bash
python scripts/final_backend_smoke.py --mode claude --require-claude-success
```

Claude smoke is manual/local only. Unit tests and CI do not require `ANTHROPIC_API_KEY`.

Safe Anthropic config diagnostics:

```bash
python scripts/check_anthropic_config.py
docker compose exec api python scripts/check_anthropic_config.py
```

This prints only key-source metadata such as presence, length, prefix validation, placeholder detection, and selected source. It never prints the key value.

Optional Claude generation quality check:

```bash
python evals/rag_generation_eval.py --mode claude --limit 5 --output reports/rag_generation_eval_report_claude_5.json
```

## Memory behavior

- Long-term memory is explicit-only through `write_memory`.
- Memory rows store redacted text plus metadata and, when the local MiniLM embedder and Postgres vector support are available, a 384-dim embedding in pgvector.
- `POST /memory/search` supports `vector`, `text`, and `hybrid` modes.
- In dev/test, the service can fall back to text-only memory search if the embedder or vector support is unavailable and `API_ALLOW_MEMORY_TEXT_FALLBACK=true`.
- PostgreSQL deployments now create a pgvector ANN index for memory embeddings when supported. Production tuning, recall validation, and scaling are still future work.

## Widget origin policy

- Public widget config and `/widget.js` check `allowed_origins` against `Origin` or `Referer` when present.
- `/widget.js` emits `Content-Security-Policy: frame-ancestors ...` based on the widget config.
- Missing origin headers are only tolerated for the localhost demo path when `API_ENABLE_DEMO_WIDGET_FALLBACK=true`.
- Production should not use wildcard origins.

## Startup validation

When `API_REQUIRE_VAULT=true`, startup now validates Vault reachability and required secret resolution for the JWT signing key. Anthropic secret resolution is also enforced if `API_REQUIRE_LLM_KEY=true`.

Optional stricter gates:

- `API_REQUIRE_MODEL_SERVER_HEALTH=true`
- `API_REQUIRE_TRACING=true`
- `API_VALIDATE_EVAL_THRESHOLDS=true`

DB and MinIO secret-path enforcement is validated at startup, and local Vault seed/check scripts now make the demo flow reproducible. Production policy and rotation still depend on deployment rollout.

Local Vault demo flow:

```bash
docker compose --env-file .env.example up -d vault
python scripts/seed_vault_dev_secrets.py
python scripts/check_vault_secrets.py
API_REQUIRE_VAULT=true ../../.venv/bin/uvicorn maintcopilot_api.main:app --reload --port 8000
```

Rate limiting:

- Enable with `API_RATE_LIMIT_ENABLED=true`.
- Redis fixed-window counters protect the global API surface plus tighter `/chat`, `/chat/stream`, widget config, and `/widget.js` limits.
- Local/demo defaults remain `API_RATE_LIMIT_FAIL_OPEN=true`; production should review thresholds and fail-open vs fail-closed behavior.

Chat orchestration smoke examples:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{
    "message": "Classify this issue",
    "context": {
      "issue_title": "Memory leak in https.request",
      "issue_body": "Repeated requests increase memory usage..."
    },
    "use_llm": false
  }'
```

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"message": "How do I debug a memory leak in https request?", "use_llm": false}'
```

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"message": "Remember that authentication issues with missing JWT should be treated as bugs.", "use_llm": false}'
```

`/chat` uses one Claude tool-calling LLM as the primary runtime path when enabled; it is not a multi-agent workflow. If `use_llm` is omitted, the API defaults to `API_CHAT_LLM_ENABLED`. If a request explicitly sends `use_llm=false`, the deterministic router is used directly. If Claude is unavailable and fallback is enabled, the response switches to `mode="deterministic_fallback"` and reports a redacted `fallback_reason` such as `llm_auth_failed`, `llm_timeout`, `llm_missing_key`, or `llm_unavailable`.

Manual Claude chat smoke is optional. Start the API with:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
API_ALLOW_IN_MEMORY_MEMORY=true
API_CHAT_ALLOW_ENV_KEY_FALLBACK=true
ANTHROPIC_API_KEY=...
```

Then run:

```bash
python scripts/final_backend_smoke.py --mode claude --require-claude-success
```

The smoke script prints mode, selected tool, citation count, and a compact answer summary. It never prints API keys. Keep `.env.local` ignored and do not commit secrets.

Available chat tools are `classify_issue`, `extract_entities`, `summarize_thread`, `rag_answer`, and `write_memory`. Short-term memory uses Redis with a 2-hour TTL. In-memory memory is dev/test only and requires `API_ALLOW_IN_MEMORY_MEMORY=true`. Long-term memory is only written through explicit `write_memory`, and all memory/logging paths use redaction.

Widget demo workflow:

For local demo mode, either create a public widget config row with `public_widget_id="demo-widget"` through the admin widget API or enable the dev-only fallback with `API_ENABLE_DEMO_WIDGET_FALLBACK=true`. Production should keep that fallback disabled.

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_ALLOW_IN_MEMORY_MEMORY=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
cd services/api
../../.venv/bin/uvicorn maintcopilot_api.main:app --reload --port 8000
```

```bash
cd services/widget
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open `demo/host/index.html` directly in a browser, or serve `demo/host` statically. Use `http://localhost:8090` if serving it on a port so the dev fallback allowed origins match. The host uses the API loader:

```html
<script
  src="http://localhost:8000/widget.js"
  data-widget-id="demo-widget"
  data-api-base-url="http://localhost:8000"
  data-widget-url="http://localhost:5173">
</script>
```

The widget loads backend config from `/widgets/{widget_id}/config`, uses `theme.primaryColor`, `theme.position`, `greeting`, `enabled_tools`, and `default_use_llm`, then calls `/chat` with `use_llm` set from that backend config. Production should keep auth enabled and enforce origin allowlisting.

Build and smoke-check:

```bash
cd services/widget
npm install
npm run build
```

```bash
python scripts/build_widget_bundle_report.py
```

```bash
python scripts/smoke_chat.py --widget-config
python scripts/smoke_chat.py --mode fallback --chat-rag
python scripts/smoke_chat.py --chat-classify
```

The build writes `services/widget/dist`. The current demo still serves the widget through the widget service; production delivery is the built `dist` bundle served from a trusted static host and referenced by `data-widget-url`.

## Docker integration

Validate the Compose file:

```bash
docker compose --env-file .env.example config
```

Build the Docker images:

```bash
docker compose --env-file .env.example build api model-server widget chatbot
```

Start the backend stack with dev-only flags for the local demo:

```bash
API_REQUIRE_VAULT=false \
API_AUTH_OPTIONAL_FOR_DEV=true \
API_CHAT_LLM_ENABLED=false \
API_ENABLE_DEMO_WIDGET_FALLBACK=true \
API_ALLOW_IN_MEMORY_MEMORY=true \
docker compose --env-file .env.example up -d postgres redis minio vault model-server api
```

Health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

Smoke checks:

```bash
python scripts/smoke_chat.py --widget-config
python scripts/smoke_chat.py --mode fallback --chat-rag
python scripts/smoke_chat.py --chat-classify
```

Stop the stack when finished:

```bash
docker compose --env-file .env.example down
```

Docker notes:

- `.env.local` is local-only, ignored by git, and must not be copied into images.
- Production should not enable `API_AUTH_OPTIONAL_FOR_DEV` or `API_ENABLE_DEMO_WIDGET_FALLBACK`.
- The API container expects the local Hugging Face cache at `${HOME}/.cache/huggingface` so offline dense retrieval can load `sentence-transformers/all-MiniLM-L6-v2`.
- The local reranker model path is `artifacts/rag/reranker_model`.

## CI workflow

`.github/workflows/ci.yml` runs on push and pull request. It covers API tests, model-server tests, widget build, eval gates, Docker config/build, and redaction/security checks.

CI does not require Claude secrets and must not call real Claude. If Git LFS artifacts are missing, the eval job fails clearly with `git lfs pull` instructions rather than silently skipping model-backed checks.

## Local Dev Service URLs

- API base URL: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Model-server base URL: `http://localhost:8001`
- Model-server docs: `http://localhost:8001/docs`
- Vault UI: `http://localhost:8200/ui`
  Vault dev root token comes from `VAULT_DEV_ROOT_TOKEN_ID` in `.env` and `docker-compose.yml`.
- Jaeger UI: `http://localhost:16686`
  Generate a trace by calling `/chat` or `/rag/answer`, then inspect recent redacted events at `/observability/recent?limit=20`.
- MinIO console: `http://localhost:9001`
  MinIO dev credentials come from `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` in `.env` and `docker-compose.yml`.
- MinIO API: `http://localhost:9000`

These URLs and credentials are for development only. Application code must read secrets through config and the eventual Vault secret path, never from hardcoded literals.

## Claude LLM baseline

- Production/deployed API path: Anthropic key resolution must come from Vault via `API_ANTHROPIC_API_KEY_SECRET_PATH`.
- Local one-off baseline path: `ANTHROPIC_API_KEY` fallback is allowed only for development. Use an ignored `.env.local` file or export it in your shell.

Local setup:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with:

```bash
API_REQUIRE_VAULT=false
ANTHROPIC_API_KEY=your-key-here
```

Dry-run:

```bash
python scripts/run_llm_baseline.py --dry-run --limit 5
```

Real local development run:

```bash
python scripts/run_llm_baseline.py --model-name claude-haiku-4-5-20251001 --allow-env-key
```

Warnings:

- Do not commit API keys.
- Do not paste API keys into Codex.
- Do not use dry-run metrics as final metrics.

## Core endpoints

- API health: `GET /health`
- API readiness: `GET /ready`
- Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/invites`, `POST /auth/invites/accept`
- Widget public config: `GET /widgets/{public_widget_id}/config`
- Widget admin: `GET /admin/widgets`, `POST /admin/widgets`, `PATCH /admin/widgets/{public_widget_id}`, `DELETE /admin/widgets/{public_widget_id}`
- Model server health: `GET /health`
- Model contracts: `POST /classify`, `POST /ner`, `POST /summarize`

## Notes

- Set `API_REQUIRE_VAULT=false` for unit tests that should not depend on Vault reachability.
- Classifier artifacts are expected later under `artifacts/classifier/`.
- The `migrate` service runs `alembic upgrade head` against the shared Postgres instance.

## ML Artifact Handoff

Copy Colab outputs into:

- `data/raw/`
- `data/processed/`
- `data/golden/`
- `artifacts/classifier/classical/`
- `artifacts/classifier/transformer/`
- `artifacts/classifier/llm_baseline/`
- `artifacts/classifier/comparison/`
- `reports/`

Verify after copying:

```bash
python scripts/verify_ml_artifacts.py --allow-missing-llm
```

Git LFS setup:

```bash
git lfs install
git lfs track "*.safetensors"
git lfs track "*.joblib"
git lfs track "*.bin"
git lfs track "*.pkl"
git lfs track "*.onnx"
git lfs track "data/raw/*.jsonl"
git lfs track "data/processed/*.jsonl"
git lfs track "data/golden/*.jsonl"
git lfs track "artifacts/**/*.jsonl"
```

Safe staging:

```bash
git add .gitattributes
git add data artifacts reports scripts/verify_ml_artifacts.py
```

Warnings:

- Do not commit model artifacts before Git LFS is configured.
- Do not use `git add .` blindly.
- Run `git lfs ls-files` before commit.
- If expected artifact files are missing after clone, run `git lfs pull`.
- The model-server classifier artifacts are tracked with Git LFS and must be present locally for real `/classify` inference.

## Docker bootstrap

1. Run Docker Compose.
2. Wait for `migrate`, `api`, and `model-server` to become healthy.
