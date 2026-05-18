# Architecture

## Layering

- `app/api`: HTTP transport only. Routers depend on service interfaces and FastAPI wiring.
- `app/services`: Business orchestration, transactions, and use-case logic.
- `app/repositories`: SQL only. No HTTP concerns.
- `app/domain`: Pydantic schemas and domain exceptions.
- `app/infra`: Adapters for Vault, Redis, MinIO, tracing, logging, redaction, and model-server access.

## Service boundaries

### API

- Owns request validation, startup dependency checks, chat orchestration, memory orchestration, widget config reads, and future auth composition.
- Refuses to boot when Vault is required and unreachable.

### Model server

- Exposes stable HTTP contracts for classifier, NER, and summarizer capabilities.
- Loads future artifacts behind a single loader interface.

## Data stores

- PostgreSQL stores conversations, memories, widget config, audit logs, and retrieved chunk snapshots.
- Redis is reserved for caching, sessions, and rate-limiting primitives.
- MinIO is reserved for artifact and document object storage.
- Vault is the required secret authority outside unit-test mode.

