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
