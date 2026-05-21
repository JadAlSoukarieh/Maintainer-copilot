from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from maintcopilot_api.infra.observability import recent_events
from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.infra.tracing import get_request_id, get_trace_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "trace_id": get_trace_id(),
        }
        event_fields = getattr(record, "event_fields", {})
        if event_fields:
            payload.update(redact(event_fields))
        return json.dumps(payload, default=str)


def configure_logging(log_level: str) -> None:
    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def log_with_context(logger: logging.Logger, level: str, message: str, **fields: Any) -> None:
    log_method = getattr(logger, level.lower())
    redacted_fields = redact(fields)
    recent_events.append(message, redacted_fields)
    log_method(message, extra={"event_fields": redacted_fields})
