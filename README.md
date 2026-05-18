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
4. Run the API locally:
   `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
5. Run the model server locally:
   `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
6. Run both Python test suites:
   `./.venv/bin/python scripts/run_tests.py`

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

See `ARCH.md`, `DECISIONS.md`, `RUNBOOK.md`, `SECURITY.md`, and `EVALS.md` for the operational skeleton.
