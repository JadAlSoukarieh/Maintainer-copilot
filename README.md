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
- No real auth, LLM, RAG, or training logic is implemented yet.

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
