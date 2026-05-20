# Maintainer's Copilot

Week 7 monorepo foundation for an authenticated maintainer assistant. This repository intentionally ships only the production skeleton: bootable services, interfaces, contracts, migrations, placeholder UI surfaces, and operational docs.

## Services

- `services/api`: FastAPI orchestration service for chat, memory, widget config, readiness, and future auth.
- `services/model-server`: FastAPI model facade with placeholder classifier, NER, and summarization endpoints.
- `services/chatbot`: Streamlit placeholder surface.
- `services/widget`: Vite React widget placeholder.
- `demo/host`: Static host placeholder for widget embedding.

## Supporting infra

- PostgreSQL 16 with pgvector
- Redis
- MinIO
- Vault dev mode
- Alembic migration runner

## Current scope

- Contracts and startup guards are in place.
- Vault reachability is required by default for the API service.
- Model-serving responses are deterministic placeholders.
- Auth foundation, classifier inference, NER, summarization, and the RAG corpus baseline skeleton are implemented.
- Dense retrieval, hybrid retrieval, deterministic query rewrite, metadata-aware boosting, local reranking, the extractive RAG answer endpoint, and `/chat` tool orchestration are implemented. Final generative RAG beyond tool-grounded chat is still not implemented.

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
   `API_CHAT_LLM_ENABLED=false`
   `API_ALLOW_IN_MEMORY_MEMORY=true`
4. Run the API locally:
   `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
5. Run the model server locally:
   `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
6. Run both Python test suites:
   `./.venv/bin/python scripts/run_tests.py`

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
```

RAG corpus build and retrieval smoke check:

```bash
python scripts/build_rag_corpus.py \
  --issues-path data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl \
  --docs-dir data/rag/raw/node_docs \
  --out data/rag/processed/rag_corpus.jsonl \
  --smoke-query "How do I debug memory leak in https request?"
```

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

The baseline retriever is sparse TF-IDF. Dense retrieval uses local `sentence-transformers/all-MiniLM-L6-v2` embeddings, hybrid retrieval combines normalized sparse and dense scores, deterministic query rewrite expands Node-specific terms without an LLM, and metadata boosting gives a small explainable score bump for matching source type or module metadata. Reranking uses a local cross-encoder over retrieved candidates. Generation is still future work.

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

`/rag/answer` returns an extractive fallback answer, rewritten query, citations, and diagnostics. It does not call Claude or external APIs. Optional `source_type` can restrict retrieval to `doc` or `resolved_issue`; by default metadata boosting is a small ranking signal, not a hard filter. When the local reranker model path exists, the service prefers reranked retrieval. Otherwise it falls back to hybrid plus rewrite and boost and reports that fallback in diagnostics. The final chatbot RAG tool should require authentication before production use.

## Chat Orchestration

`POST /chat` is the Maintainer's Copilot orchestration endpoint. It uses one Claude tool-calling LLM when configured; this is not a multi-agent workflow. If Claude is disabled or unavailable and fallback is enabled, the deterministic router selects one tool and the response includes `mode="deterministic_fallback"` plus `fallback_reason`.

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
- Memory and logs pass through redaction before storage/emission.

Fallback-only local mode:

```bash
API_CHAT_LLM_ENABLED=false
API_ALLOW_IN_MEMORY_MEMORY=true
```

Claude mode uses `API_ANTHROPIC_API_KEY_SECRET_PATH` through Vault. For local development only, env fallback is available when `API_REQUIRE_VAULT=false`; do not commit API keys.

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

The React widget reads `widget_id` and `api_base_url` from the iframe URL, loads `GET /widgets/{widget_id}/config`, applies the configured greeting/theme/tools, then sends chat messages to `POST /chat` with `use_llm=false` by default. That keeps the demo deterministic and independent of Claude/internet.

The demo expects a public widget config row with `public_widget_id="demo-widget"`. Create it through the admin widget API before opening the host page.

For an unauthenticated local widget demo, run the API with:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=false
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
