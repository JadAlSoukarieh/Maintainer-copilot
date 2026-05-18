# Runbook

## Local bootstrap

1. Create and activate the repo-local virtual environment:
   `python3 -m venv .venv`
   `source .venv/bin/activate`
2. Bootstrap Python dependencies:
   `python scripts/bootstrap_dev.py`
3. Copy `.env.example` to `.env` when you need local environment variables.

## Local runs

- API:
  `cd services/api && ../../.venv/bin/python -m uvicorn maintcopilot_api.main:app --reload`
- Model server:
  `cd services/model-server && ../../.venv/bin/python -m uvicorn maintcopilot_model_server.main:app --reload`
- Tests:
  `./.venv/bin/python scripts/run_tests.py`

## Core endpoints

- API health: `GET /health`
- API readiness: `GET /ready`
- Model server health: `GET /health`
- Model contracts: `POST /classify`, `POST /ner`, `POST /summarize`

## Notes

- Set `API_REQUIRE_VAULT=false` for unit tests that should not depend on Vault reachability.
- Classifier artifacts are expected later under `artifacts/classifier/`.
- The `migrate` service runs `alembic upgrade head` against the shared Postgres instance.

## Docker bootstrap

1. Run Docker Compose.
2. Wait for `migrate`, `api`, and `model-server` to become healthy.
