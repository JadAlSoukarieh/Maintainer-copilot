# Local Demo Checklist

This checklist is for local development only.

## API environment

Use these flags for the normal local demo where Claude is the primary runtime path:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_CHAT_ALLOW_ENV_KEY_FALLBACK=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
API_ALLOW_IN_MEMORY_MEMORY=true
```

For a fully offline reproducible fallback demo, switch only this flag:

```bash
API_CHAT_LLM_ENABLED=false
```

Production should keep auth enabled, keep `API_ENABLE_DEMO_WIDGET_FALLBACK=false`, use Redis for short-term memory, and resolve secrets through Vault.

## Run API

```bash
cd services/api
../../.venv/bin/uvicorn maintcopilot_api.main:app --reload --port 8000
```

## Run widget

```bash
cd services/widget
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Open demo host

Open `demo/host/index.html` directly in a browser, or serve `demo/host` statically.

The page embeds:

```html
<script
  src="http://localhost:8000/widget.js"
  data-widget-id="demo-widget"
  data-api-base-url="http://localhost:8000"
  data-widget-url="http://localhost:5173">
</script>
```

## Smoke checks

```bash
python scripts/smoke_chat.py --widget-config
python scripts/smoke_chat.py --mode fallback --chat-rag
python scripts/smoke_chat.py --chat-classify
python scripts/check_anthropic_config.py
```

A successful chat smoke check prints `selected_tool`, `mode`, `conversation_id`, and the first part of the assistant message. In fallback mode, `mode` should be `deterministic_fallback`.

## Optional Claude smoke

For one manual Claude tool-calling smoke, start the API with:

```bash
API_REQUIRE_VAULT=false
API_AUTH_OPTIONAL_FOR_DEV=true
API_CHAT_LLM_ENABLED=true
API_ENABLE_DEMO_WIDGET_FALLBACK=true
API_ALLOW_IN_MEMORY_MEMORY=true
API_CHAT_ALLOW_ENV_KEY_FALLBACK=true
ANTHROPIC_API_KEY=...
```

Then run:

```bash
python scripts/smoke_chat.py --mode claude --chat-rag
```

Do not commit `.env.local` or paste API keys into logs, docs, or prompts.
