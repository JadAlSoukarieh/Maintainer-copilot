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
3. Run the API locally:
   `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
4. Run the model server locally:
   `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
5. Run both Python test suites:
   `./.venv/bin/python scripts/run_tests.py`

See `ARCH.md`, `DECISIONS.md`, `RUNBOOK.md`, `SECURITY.md`, and `EVALS.md` for the operational skeleton.
