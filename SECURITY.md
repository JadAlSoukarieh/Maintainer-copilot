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
- CI and tests do not require `ANTHROPIC_API_KEY` and must not call real Claude.
- Streamlit demo mode depends on `API_AUTH_OPTIONAL_FOR_DEV=true`; production should require auth.
- Recent events/request IDs are redacted lightweight diagnostics, not a full tracing backend.
- Long-term memory is explicit-only and now supports pgvector-backed episodic embeddings when the local MiniLM embedder and Postgres vector support are available. Text-only fallback remains configurable for dev/test and should be disabled in stricter production deployments.
- Redis fixed-window rate limiting is implemented for the global API surface with tighter limits for `/chat`, `/chat/stream`, widget config, and `/widget.js`. `/health` remains effectively exempt, and the default local/demo mode is fail-open if Redis is unavailable.
- Public widget delivery now enforces configured `allowed_origins` at the widget config and loader surface when `Origin` or `Referer` is present, and emits `Content-Security-Policy: frame-ancestors ...` for embed control.

## Redaction patterns

All log emission and memory storage paths run through `infra/redaction.py` before output. The following patterns are matched and replaced with `[REDACTED]`:

| # | Pattern | Covers |
|---|---|---|
| 1 | `\bsk-[A-Za-z0-9_-]+\b` | Anthropic / OpenAI API keys |
| 2 | `\bsk-ant-[A-Za-z0-9_-]+\b` | Anthropic API keys (long form) |
| 3 | `\bghp_[A-Za-z0-9]+\b` | GitHub personal access tokens |
| 4 | `\bgithub_pat_[A-Za-z0-9_]+\b` | GitHub fine-grained PATs |
| 5 | `Bearer\s+[A-Za-z0-9\-._~+/]+=*` | HTTP Authorization bearer tokens, case-insensitive |
| 6 | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b` | Email addresses |
| 7 | `(?i)\b(password\|passwd\|pwd\|secret)\s*=\s*([^\s,;]+)` | Key=value credential pairs |

Redaction runs in `infra/redaction.py::redact()` as a recursive walk over dicts, lists, tuples, and strings. It is applied in:

- short-term chat memory for every user/assistant turn
- `MemoryService.create()` before persistence
- `/chat` responses on message and tool-result fields
- structured log fields via `log_with_context()`

Gaps / deferred hardening:

- Redaction is text-only. Binary blobs, JSON-encoded nested strings, and base64-encoded values are not decoded before matching.
- Regex patterns are evaluated over provided text payloads; unusually large payloads may add latency.

## Deferred work

- Full production Vault policy rollout for every secret dependency and environment
- Audit log coverage for future destructive memory operations; no memory DELETE endpoint currently exists.
- Encryption-at-rest and KMS integration
- Production tracing operations such as sampling policy, retention, alerting, and trace-SLO dashboards
- Abuse tuning, threshold calibration, and operational policy review for the Redis rate limiter
- Retention policy and operational tuning for pgvector-backed long-term memory
