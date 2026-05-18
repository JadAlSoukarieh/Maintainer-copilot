# Architectural Decisions

1. The API service is split into transport, service, repository, domain, and infra layers to keep external dependencies out of routers.
2. Vault reachability is checked during API startup so missing secret infrastructure fails early instead of surfacing later as partial runtime errors.
3. Structured logging is implemented with request and trace correlation fields plus centralized redaction before emission.
4. Placeholder model-server outputs are deterministic so downstream integration can start before classifier artifacts exist.
5. Widget configuration is modeled in SQL from day one because embedding policy and theming are operational data, not frontend constants.

