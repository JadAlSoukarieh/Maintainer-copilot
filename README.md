# Maintainer's Copilot

Week 7 monorepo for an authenticated Maintainer's Copilot. It includes the API orchestration service, real RoBERTa issue classification, local RAG retrieval and extractive answers, a React embedded widget, a Streamlit internal console, Docker Compose integration, and regression eval gates.

## Services

- `services/api`: FastAPI orchestration service for auth, chat, memory, widget config, RAG, reports, and observability.
- `services/model-server`: FastAPI model facade with artifact-backed RoBERTa `/classify`, rule-based `/ner`, and extractive `/summarize`.
- `services/chatbot`: Streamlit internal/admin console that calls the API only.
- `services/widget`: Vite React embedded widget for the public/demo surface.
- `demo/host`: Static host page for widget embedding.

## Supporting infra

- PostgreSQL 16 with pgvector
- Redis
- MinIO
- Vault dev mode
- Alembic migration runner

## Current scope

- Vault reachability remains required by default for deployed API startup.
- Auth foundation, classifier inference, NER, summarization, `/chat`, `/rag/answer`, widget config, and demo-widget fallback are implemented.
- Dense retrieval, hybrid retrieval, deterministic query rewrite, metadata-aware boosting, local reranking, extractive RAG answers, and deterministic fallback chat orchestration are implemented.
- RAG generation evaluation is a deterministic offline regression gate over the extractive answer path. Claude generation is optional/manual only and is not used in tests or CI.
- Recent events/request IDs are lightweight observability, not a full tracing backend.
- Long-term memory is explicit-only episodic memory with pgvector-capable 384-dim MiniLM embeddings when the local embedder and Postgres vector support are available. Dev/test can still fall back to text-only memory when configured.

## Brief compliance status

Completed:

- classifier comparison and frozen artifact verification
- real model-server inference for classification, NER, and summarization
- advanced RAG retrieval with dense, hybrid, reranked, rewrite, and metadata boost paths
- `/chat` orchestration with Claude tool-calling as the primary runtime mode and deterministic fallback as the backup path
- React widget demo and Streamlit internal console
- Docker Compose stack and CI workflow
- RAG retrieval and deterministic generation eval gates

Partial / intentionally honest deviations:

- auth still uses the custom invite/JWT flow as the primary application path, even though `fastapi-users` routes are wired at `/auth/v2` and `/users/v2` for compliance/future migration
- Vault startup validation plus local seed/check scripts are implemented, but production policy, rotation, and environment rollout still depend on concrete deployment practices
- observability includes OTEL/Jaeger spans plus recent-event diagnostics for project/demo scope, not a full production tracing operations program
- long-term memory now has a pgvector ANN index path, but production tuning and scaling remain future work
- resolved issue title/body remains the default corpus input; optional issue-comment sample ingestion exists, but full historical maintainer-comment coverage is not implemented
- the widget demo still runs through the widget service; production bundle delivery is proved via build artifacts and bundle reports rather than a single API-hosted bundle

## Local development

1. Create and activate the repo-local virtual environment:
   `python3 -m venv .venv`
   `source .venv/bin/activate`
2. Bootstrap dependencies and editable installs:
   `python scripts/bootstrap_dev.py`
3. Set local API auth config in `.env`:
   `API_REQUIRE_VAULT=false`
   `API_JWT_SECRET=dev-only-jwt-secret-change-me`
   `API_REQUIRE_LLM_KEY=false`
   `API_CHAT_LLM_ENABLED=true`
   `API_CHAT_ALLOW_ENV_KEY_FALLBACK=true`
   `API_ALLOW_IN_MEMORY_MEMORY=true`
   `ANTHROPIC_API_KEY=...` for live Claude mode, or leave the key unset and use deterministic fallback requests only
4. Run the API locally:
   `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
5. Run the model server locally:
   `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
6. Run both Python test suites:
   `./.venv/bin/python scripts/run_tests.py`

## Streamlit Internal Console

The internal/admin Streamlit app runs at `http://localhost:8501` in Docker and is separate from the React embedded widget. Streamlit is an API client only: it calls FastAPI endpoints and does not duplicate classifier, RAG, or model-server logic.

Tabs:

- Chat: full `/chat` UI with issue context, Claude tool-calling as the default runtime path when enabled, deterministic fallback badge/reason reporting, citations, request IDs, and conversation state.
- Issue Tools: maintainer workbench for classify, entity extraction, summarization, and RAG through `/chat`.
- Widget Admin: list/create/update/disable widgets and generate embed snippets.
- Evals / Metrics: reads `/reports/summary` for classifier, RAG retrieval, and RAG generation metrics.
- Memory Inspector: shows short-term chat memory plus pgvector-capable episodic long-term memories, with explicit vector/text fallback diagnostics.
- Logs / Observability: lightweight recent events and Docker log commands, not full OpenTelemetry/Jaeger tracing.

Run locally:

```bash
cd services/chatbot
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Run through Docker:

```bash
docker compose --env-file .env.example up -d chatbot
```

Use demo mode only with `API_AUTH_OPTIONAL_FOR_DEV=true`; production should require auth.

Model-server classifier smoke check:

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

`--model all --gate primary` evaluates the same 25-example golden set across the selected transformer, the classical baseline, and frozen LLM baseline predictions when those artifacts exist. Only the deployed selected transformer blocks by default. Baseline failures are reported honestly as warnings unless `--gate all` or `--strict-baselines` is used. This remains a regression gate, not the primary model-selection metric; the full 196-example frozen test split is still the main quality reference.

Dev-only MLflow training run logging:

```bash
python scripts/log_training_run.py
mlflow ui --backend-store-uri mlruns --port 5000
```

This reads the frozen RoBERTa metrics, training args, and comparison report from `artifacts/classifier/` and logs them to local `mlruns/`. MLflow is listed in top-level `requirements-dev.txt` only; it is not part of the API runtime image.

RAG corpus build and retrieval smoke check:

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

This does not run in CI and is not required for the committed eval path. If `data/rag/raw/issue_comments_sample.jsonl` exists, the corpus builder adds `issue_comment` chunks; otherwise the default resolved-issue title/body corpus remains unchanged.

Model-server NER smoke check:

```bash
curl -X POST http://localhost:8001/ner \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "fs.utimes fails on v6.5.0",
    "body": "See /usr/local/lib/node_modules/app/index.js and https://nodejs.org/docs. Call crypto.pbkdf2() with --trace-warnings."
  }'
```

Model-server summarizer smoke check:

```bash
curl -X POST http://localhost:8001/summarize \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Memory leak in https.request",
    "body": "Version: v6.8.0. Platform: Ubuntu 16.04. Repro: send many requests. Actual: memory grows after ECONNRESET.",
    "max_bullets": 3
  }'
```

`/ner` is rule-based and `/summarize` is extractive for now. They are integration tools for the future chatbot workflow, not LLM-backed features yet.

The RAG foundation currently builds a local corpus from:

- Node.js docs placed under `data/rag/raw/node_docs`
- held-out resolved Node.js issues from the validation, test, and excluded splits

Current limitation: resolved issue chunks use issue title/body only. Maintainer comments and closing answers are not yet ingested, so retrieval over resolved issues is grounded in the issue record rather than the full issue discussion.

The baseline retriever is sparse TF-IDF. Dense retrieval uses local `sentence-transformers/all-MiniLM-L6-v2` embeddings, hybrid retrieval combines normalized sparse and dense scores, deterministic query rewrite expands Node-specific terms without an LLM, metadata boosting gives a small explainable score bump for matching source type or module metadata, and reranking uses a local cross-encoder over retrieved candidates.

To prepare local Node docs for corpus builds:

```bash
git clone --depth 1 https://github.com/nodejs/node.git /tmp/node
mkdir -p data/rag/raw/node_docs
cp -r /tmp/node/doc/api data/rag/raw/node_docs/api
```

Then rebuild the corpus:

```bash
python scripts/build_rag_corpus.py \
  --issues-path data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl \
  --docs-dir data/rag/raw/node_docs \
  --out data/rag/processed/rag_corpus.jsonl \
  --smoke-query "How do I debug memory leak in https request?"
```

Local docs are required before advanced RAG eval work. Without them, the corpus is issue-only.

RAG golden candidate workflow:

```bash
python scripts/make_rag_golden_candidates.py
python scripts/review_rag_golden_candidates.py
python scripts/create_rag_golden_draft.py
# candidates are not final eval data
python scripts/validate_rag_golden.py --golden-path data/rag/golden/rag_golden.jsonl --require-final
python evals/rag_retrieval_eval.py
```

The current final RAG golden set is AI-assisted curated and validated with `human_review_status=ai_assisted_approved`; it should be spot-checked before submission. Sparse TF-IDF is the baseline to beat, and sparse, dense, hybrid, and reranked retrieval have all been measured against the same golden set.

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

The embedding builder uses the local `sentence-transformers/all-MiniLM-L6-v2` model cache. It does not call an external embedding API. The reranker runs locally from `artifacts/rag/reranker_model`. If that path is missing, `/rag/answer` falls back to hybrid plus rewrite and boost and exposes the fallback in diagnostics instead of crashing the local demo.

Current RAG retrieval results:

| Retriever | Alpha | Rewrite+Boost | Rerank Top N | hit@5 | hit@10 | MRR@10 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| sparse TF-IDF | 1.00 | no | - | 0.5600 | 0.6000 | 0.3463 |
| dense MiniLM | 0.00 | no | - | 0.6000 | 0.6800 | 0.5584 |
| hybrid | 0.50 | yes | - | 0.7600 | 0.8000 | 0.6080 |
| reranked hybrid | 0.50 | no | 20 | 0.7200 | 0.7200 | 0.6280 |
| reranked hybrid | 0.50 | yes | 20 | 0.8000 | 0.8000 | 0.6280 |
| reranked hybrid, MRR-optimized sweep | 0.25 | no | 10 | 0.7200 | 0.7200 | 0.6533 |

The selected default is reranked hybrid plus deterministic query rewrite and metadata boost with `alpha=0.50` and `rerank_top_n=20`. That variant matches the best measured hit@5 at `0.8000` and still improves MRR@10 over non-reranked hybrid. The `alpha=0.25`, `rerank_top_n=10` variant is the best MRR-only configuration, but it gives up hit@5, so it is not the default for the multi-chunk answer path.

API RAG answer smoke check:

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

`/rag/answer` returns an extractive fallback answer, rewritten query, citations, and diagnostics from retrieved Node.js docs/issues. It does not call Claude or external APIs. Optional `source_type` can restrict retrieval to `doc` or `resolved_issue`; by default metadata boosting is a small ranking signal, not a hard filter. When the local reranker model path exists, the service prefers reranked retrieval. Otherwise it falls back to hybrid plus rewrite and boost and reports that fallback in diagnostics. The final chatbot RAG tool should require authentication before production use.

RAG generation eval is deterministic and offline:

```bash
python evals/rag_generation_eval.py
```

It writes `reports/rag_generation_eval_report.json` using frozen judge version `frozen-rag-judge-v1`. The initial 5 generation labels in `data/rag/golden/rag_generation_human_labels.jsonl` are marked `ai_assisted_initial`; do not claim human spot-checking until a reviewer changes them to `human_spot_checked`.

To prepare those five labels for real manual review:

```bash
python scripts/review_rag_generation_labels.py
```

That writes `reports/rag_generation_human_review.md`. Review the markdown report, edit `data/rag/golden/rag_generation_human_labels.jsonl` directly, then rerun `python evals/rag_generation_eval.py`.

Optional manual Claude generation check:

```bash
python evals/rag_generation_eval.py --mode claude --limit 5 --output reports/rag_generation_eval_report_claude_5.json
```

Claude mode is manual/local only. It requires a running API with `API_CHAT_LLM_ENABLED=true`, and it is not used in unit tests or CI. Runtime/demo mode can still be Claude-first while CI stays deterministic.

## Widget embed security

- Public widget config and `/widget.js` enforce configured `allowed_origins` when `Origin` or `Referer` is present.
- `/widget.js` returns `Content-Security-Policy: frame-ancestors ...` built from the widget's allowed origins.
- The localhost demo path still works only when `API_ENABLE_DEMO_WIDGET_FALLBACK=true`.
- Production should not use wildcard origins.

## Startup policy

When `API_REQUIRE_VAULT=true`, API startup now validates:

- Vault reachability
- JWT signing secret resolution from Vault
- Anthropic key resolution if `API_REQUIRE_LLM_KEY=true`
- nonzero eval thresholds for `classification`, `rag_retrieval`, and `rag_generation`
- tracing backend configuration if `API_REQUIRE_TRACING=true`
- model-server health if `API_REQUIRE_MODEL_SERVER_HEALTH=true`

DB and MinIO secret paths are supported, and local Vault seed/check scripts now make the demo flow reproducible. Production policy and rotation are still deployment concerns, not something this repo fully automates.

Local Vault dev flow:

```bash
docker compose --env-file .env.example up -d vault
python scripts/seed_vault_dev_secrets.py
python scripts/check_vault_secrets.py
API_REQUIRE_VAULT=true ../../.venv/bin/uvicorn maintcopilot_api.main:app --reload --port 8000
```

## Chat Orchestration

`POST /chat` is the Maintainer's Copilot orchestration endpoint. It uses one Claude tool-calling LLM when configured; this is not a multi-agent workflow. If `use_llm` is omitted, the API defaults to `API_CHAT_LLM_ENABLED`. If `use_llm=false`, the deterministic router is used directly. If Claude is disabled or unavailable and fallback is enabled, the response includes `mode="deterministic_fallback"` plus `fallback_reason`.

Available tools:

- `classify_issue`
- `extract_entities`
- `summarize_thread`
- `rag_answer`
- `write_memory`

Memory behavior:

- Short-term chat memory uses Redis with a 2-hour TTL.
- In-memory short-term memory is dev/test only and requires `API_ALLOW_IN_MEMORY_MEMORY=true`.
- Long-term memory is written only through explicit `write_memory`.
- Long-term memory stores redacted episodic text plus metadata and, when available, a 384-dim MiniLM embedding in Postgres/pgvector with an ANN index path for cosine search. If the embedder or vector support is unavailable, the service can fall back to text-only mode when configured for dev/test.
- Memory and logs pass through redaction before storage/emission.

Rate limiting:

- Redis fixed-window rate limiting is available through `API_RATE_LIMIT_ENABLED=true`.
- Global and tighter `/chat` and widget-public-surface limits are configured separately.
- The default is `fail_open` for local/demo safety; production tuning should review thresholds and whether backend failure should close requests instead.

Fallback-only local mode:

```bash
API_CHAT_LLM_ENABLED=false
API_ALLOW_IN_MEMORY_MEMORY=true
```

When `API_REQUIRE_VAULT=true`, Claude key resolution prefers `API_ANTHROPIC_API_KEY_SECRET_PATH` through Vault and fails cleanly if the Vault value is missing or still a placeholder. For local development only, env fallback is available when `API_REQUIRE_VAULT=false` and `API_CHAT_ALLOW_ENV_KEY_FALLBACK=true`; do not commit API keys.

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

Safe Anthropic config diagnostics:

```bash
python scripts/check_anthropic_config.py
docker compose exec api python scripts/check_anthropic_config.py
```

The diagnostic prints only presence, length, prefix validation, placeholder detection, and selected source. It never prints the key value.

## Final backend smoke

Run deterministic backend smoke against a running local stack:

```bash
python scripts/final_backend_smoke.py --mode fallback
```

Run one controlled Claude smoke locally after loading `.env.local` and starting the API with env-key fallback enabled:

```bash
python scripts/final_backend_smoke.py --mode claude --require-claude-success
```

The smoke report is written to `reports/final_backend_smoke_report.json` and redacts secret-like values. Claude smoke is manual/local only and is not used in unit tests or CI.

For a small manual Claude answer-quality pass over RAG generation:

```bash
python evals/rag_generation_eval.py --mode claude --limit 5 --output reports/rag_generation_eval_report_claude_5.json
```

For Docker fallback demo:

```bash
API_REQUIRE_VAULT=false \
API_AUTH_OPTIONAL_FOR_DEV=true \
API_CHAT_LLM_ENABLED=false \
API_ENABLE_DEMO_WIDGET_FALLBACK=true \
API_ALLOW_IN_MEMORY_MEMORY=true \
docker compose --env-file .env.example up -d
```

For Docker Claude smoke, keep `.env.local` ignored, load it locally, then start with explicit dev flags:

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

The smoke script never prints API keys. Keep `.env.local` ignored and do not commit secrets.

Chat classify example:

```json
{
  "message": "Classify this issue",
  "context": {
    "issue_title": "Memory leak in https.request",
    "issue_body": "Repeated requests increase memory usage..."
  }
}
```

Chat RAG example:

```json
{
  "message": "How do I debug a memory leak in https request?"
}
```

Chat memory example:

```json
{
  "message": "Remember that authentication issues with missing JWT should be treated as bugs."
}
```

## Widget Demo

The React widget reads `widget_id` and `api_base_url` from the iframe URL, loads `GET /widgets/{widget_id}/config`, applies the configured greeting/theme/tools, and follows `default_use_llm` from the backend config when sending `POST /chat`. When `API_CHAT_LLM_ENABLED=true`, the widget uses Claude/tool-calling first; if the backend falls back, the UI shows a deterministic fallback badge and reason.

Production bundle proof:

- `npm run build` writes the bundle to `services/widget/dist`.
- `python scripts/build_widget_bundle_report.py` records built asset paths and sizes to `reports/widget_bundle_report.json`.
- The current demo still points `/widget.js` at the widget service URL. The documented production path is `dist -> CDN/MinIO/static host -> widget_url`.

For local demo mode, either create a public widget config row with `public_widget_id="demo-widget"` through the admin widget API or enable the dev-only fallback with `API_ENABLE_DEMO_WIDGET_FALLBACK=true`. Production should keep that fallback disabled.

For an unauthenticated local widget demo, run the API with:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_ALLOW_IN_MEMORY_MEMORY=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
```

Start the API:

```bash
cd services/api
../../.venv/bin/uvicorn maintcopilot_api.main:app --reload --port 8000
```

Start the widget:

```bash
cd services/widget
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open `demo/host/index.html` directly in a browser, or serve `demo/host` with any static file server. If you serve the host on a port, use `http://localhost:8090` to match the dev fallback allowed origins. The demo host embeds:

```html
<script
  src="http://localhost:8000/widget.js"
  data-widget-id="demo-widget"
  data-api-base-url="http://localhost:8000"
  data-widget-url="http://localhost:5173">
</script>
```

Production should keep auth enabled, enforce widget origin allowlisting, and serve the widget frontend from a trusted built asset URL.

Build the widget under WSL2/Linux Node:

```bash
cd services/widget
npm install
npm run build
```

Run local smoke checks while the API is running:

```bash
python scripts/smoke_chat.py --widget-config
python scripts/smoke_chat.py --mode fallback --chat-rag
python scripts/smoke_chat.py --chat-classify
```

## Docker integration

Validate the Compose file:

```bash
docker compose --env-file .env.example config
```

Build the Docker images:

```bash
docker compose --env-file .env.example build api model-server widget chatbot
```

Start the backend stack with dev-only flags for the primary local demo path:

```bash
API_REQUIRE_VAULT=false \
API_AUTH_OPTIONAL_FOR_DEV=true \
API_CHAT_LLM_ENABLED=true \
API_CHAT_ALLOW_ENV_KEY_FALLBACK=true \
API_ENABLE_DEMO_WIDGET_FALLBACK=true \
API_ALLOW_IN_MEMORY_MEMORY=true \
docker compose --env-file .env.example up -d postgres redis minio vault model-server api
```

For a fully reproducible offline fallback-only demo, switch:

```bash
API_CHAT_LLM_ENABLED=false
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

Stop the stack when you are done:

```bash
docker compose --env-file .env.example down
```

Docker notes:

- `.env.local` is local-only, ignored by git, and must not be copied into images.
- Production should not enable `API_AUTH_OPTIONAL_FOR_DEV` or `API_ENABLE_DEMO_WIDGET_FALLBACK`.
- The API container expects the local Hugging Face cache at `${HOME}/.cache/huggingface` so offline dense retrieval can load `sentence-transformers/all-MiniLM-L6-v2`.
- The local reranker model path is `artifacts/rag/reranker_model`.

## CI

The workflow at `.github/workflows/ci.yml` runs on push and pull request:

- API tests
- model-server tests
- widget build
- eval gates: ML artifact verification, classification eval, selected RAG retrieval eval, and deterministic RAG generation eval
- Docker Compose config plus image builds for `api`, `model-server`, `widget`, and `chatbot`
- redaction/security checks for obvious committed secret patterns

CI does not require `ANTHROPIC_API_KEY` and must not call real Claude. If LFS artifacts are missing, the eval job fails with instructions to run `git lfs pull`.

## Local Dev Service URLs

- API base URL: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Model-server base URL: `http://localhost:8001`
- Model-server docs: `http://localhost:8001/docs`
- Vault UI: `http://localhost:8200/ui`
  Vault dev root token comes from `VAULT_DEV_ROOT_TOKEN_ID` in `.env` and `docker-compose.yml`.
- Jaeger UI: `http://localhost:16686`
  Call `/chat` or `/rag/answer`, then inspect traces and compare them with `GET /observability/recent?limit=20`.
- MinIO console: `http://localhost:9001`
  MinIO dev credentials come from `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` in `.env` and `docker-compose.yml`.
- MinIO API: `http://localhost:9000`

These are development-only values. App code must read secrets through the configured config and secrets path, not through hardcoded literals in source.

## Claude LLM Baseline

- Production/deployed API path: the Anthropic key lives in Vault at `API_ANTHROPIC_API_KEY_SECRET_PATH`.
- Local one-off baseline path: `ANTHROPIC_API_KEY` fallback is allowed only for development. Put it in an ignored `.env.local` file or export it in your shell.
- Do not commit API keys.
- Do not paste API keys into Codex.
- Do not use dry-run metrics as final metrics.

Local `.env.local` setup:

```bash
cp .env.local.example .env.local
```

Then edit `.env.local` and set:

```bash
API_REQUIRE_VAULT=false
ANTHROPIC_API_KEY=your-key-here
```

Dry-run command:

```bash
python scripts/run_llm_baseline.py --dry-run --limit 5
```

Real run command for local development fallback:

```bash
python scripts/run_llm_baseline.py --model-name claude-haiku-4-5-20251001 --allow-env-key
```

## ML Artifact Handoff

The transformer artifacts used by `services/model-server` are tracked with Git LFS. Run `git lfs pull` after cloning if the classifier model files are missing.

Copy Colab outputs into these locations:

- Raw dataset files: `data/raw/`
- Processed splits and manifests: `data/processed/`
- Golden classification set: `data/golden/`
- Classical classifier outputs: `artifacts/classifier/classical/`
- Transformer outputs: `artifacts/classifier/transformer/`
- Optional LLM baseline outputs: `artifacts/classifier/llm_baseline/`
- Comparison reports: `artifacts/classifier/comparison/`
- Validation and training summaries: `reports/`

Verify the handoff after copying:

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

Safe staging commands:

```bash
git add .gitattributes
git add data artifacts reports scripts/verify_ml_artifacts.py
```

Warnings:

- Do not commit model or dataset artifacts before Git LFS is configured.
- Do not use `git add .` blindly.
- Run `git lfs ls-files` before commit to confirm large files are tracked.
- If artifacts are missing after cloning, run `git lfs pull`.

See `ARCH.md`, `DECISIONS.md`, `RUNBOOK.md`, `SECURITY.md`, and `EVALS.md` for the operational skeleton.

## Submission

| Field | Value |
|---|---|
| Student | soukariehjad@gmail.com |
| Cohort | AIE Week 7 |
| Submission date | 2026-05-21 |
| Git tag | planned: `v0.1.0-week7` |
| Docker stack | `docker compose --env-file .env.example up -d` |
| Demo host | http://localhost:8080 |
| Admin console | http://localhost:8501 |
| API docs | http://localhost:8000/docs |

### Known honest deviations

- Resolved issue title/body remains the default RAG corpus input. Optional issue-comment sample ingestion exists, but full historical maintainer comment coverage is still future work.
- pgvector ANN indexing is implemented for memory embeddings, but production tuning and large-scale operational validation remain future work.
- The widget demo uses the widget service for clarity; production bundle proof currently comes from built `dist` assets and `reports/widget_bundle_report.json`, not a single API-hosted bundle.
- Auth includes `fastapi-users` routes for project/demo scope, but the original custom invite/JWT flow remains the main application auth path.
- Observability includes OpenTelemetry/Jaeger wiring and recent-event diagnostics for project/demo scope, not a complete production tracing operations program.
- MLflow training run logging is dev-only through `scripts/log_training_run.py`; MLflow is not part of API runtime requirements.
