# Security

## Current controls

- No secrets are hardcoded in source.
- `.env.example` contains dummy development values only.
- API startup requires Vault by default.
- Structured logs pass through centralized redaction for common token and credential patterns.
- Domain errors are mapped to a stable HTTP error envelope without leaking internal stack details.

## Deferred work

- Real authentication and authorization
- Secret retrieval from Vault paths and policies
- Audit log population strategy
- Encryption-at-rest and KMS integration
- Rate limiting and abuse controls

