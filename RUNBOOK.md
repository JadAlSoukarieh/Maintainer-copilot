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
   `API_CHAT_LLM_ENABLED=false`
   `API_ALLOW_IN_MEMORY_MEMORY=true`

## Local runs

- API:
  `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
- Model server:
  `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
- Tests:
  `./.venv/bin/python scripts/run_tests.py`

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
```

RAG corpus build and sparse retrieval smoke check:

```bash
python scripts/build_rag_corpus.py \
  --issues-path data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl \
  --docs-dir data/rag/raw/node_docs \
  --out data/rag/processed/rag_corpus.jsonl \
  --smoke-query "How do I debug memory leak in https request?"
```

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

`/rag/answer` is an extractive fallback over retrieved local corpus chunks. It returns citations, rewritten query, intent, and diagnostics for future chatbot tool use. It does not call Claude or external APIs. Optional `source_type` can restrict retrieval to `doc` or `resolved_issue`; otherwise metadata boost is only a small ranking signal. When the local reranker model exists, the API prefers reranked retrieval. Otherwise it falls back to hybrid plus rewrite and boost and exposes the fallback in diagnostics. Production chatbot RAG should require authenticated user access.

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

`/chat` uses one Claude tool-calling LLM when enabled; it is not a multi-agent workflow. If Claude is disabled or unavailable and fallback is enabled, the deterministic router selects one tool and the response includes `mode="deterministic_fallback"` plus `fallback_reason` when applicable.

Available chat tools are `classify_issue`, `extract_entities`, `summarize_thread`, `rag_answer`, and `write_memory`. Short-term memory uses Redis with a 2-hour TTL. In-memory memory is dev/test only and requires `API_ALLOW_IN_MEMORY_MEMORY=true`. Long-term memory is only written through explicit `write_memory`, and all memory/logging paths use redaction.

Widget demo workflow:

Create a public widget config row with `public_widget_id="demo-widget"` through the admin widget API before opening the host page.

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=false
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

The widget loads backend config from `/widgets/{widget_id}/config`, uses `theme.primaryColor`, `theme.position`, `greeting`, and `enabled_tools`, then calls `/chat` with `use_llm=false`. Production should keep auth enabled and enforce origin allowlisting.

Build and smoke-check:

```bash
cd services/widget
npm install
npm run build
```

```bash
python scripts/smoke_chat.py --widget-config
python scripts/smoke_chat.py --chat-rag
python scripts/smoke_chat.py --chat-classify
```

## Local Dev Service URLs

- API base URL: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Model-server base URL: `http://localhost:8001`
- Model-server docs: `http://localhost:8001/docs`
- Vault UI: `http://localhost:8200/ui`
  Vault dev root token comes from `VAULT_DEV_ROOT_TOKEN_ID` in `.env` and `docker-compose.yml`.
- MinIO console: `http://localhost:9001`
  MinIO dev credentials come from `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` in `.env` and `docker-compose.yml`.

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
