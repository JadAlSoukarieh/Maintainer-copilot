# Security

## Current controls

- No secrets are hardcoded in source.
- `.env.example` contains dummy development values only.
- API startup requires Vault by default.
- Structured logs pass through centralized redaction for common token and credential patterns.
- Domain errors are mapped to a stable HTTP error envelope without leaking internal stack details.
- `/chat` treats issue text, retrieved chunks, and tool outputs as untrusted context.
- `/chat` long-term memory writes are explicit-only through `write_memory`; memory and logging paths pass through redaction.
- In-memory short-term chat memory is dev/test only and requires `API_ALLOW_IN_MEMORY_MEMORY=true`; production should use Redis.
- The demo widget fallback is disabled by default and only applies to `public_widget_id=demo-widget` when `API_ENABLE_DEMO_WIDGET_FALLBACK=true`.

## Deferred work

- Secret retrieval from Vault paths and policies
- Audit log population strategy
- Encryption-at-rest and KMS integration
- Rate limiting and abuse controls
