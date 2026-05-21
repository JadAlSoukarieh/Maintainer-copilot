from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.infra.tracing import get_request_id, get_trace_id


class RecentEventBuffer:
    def __init__(self, *, maxlen: int = 200) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = Lock()

    def append(self, event_name: str, fields: dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_name,
            "request_id": get_request_id(),
            "trace_id": get_trace_id(),
            "fields": redact(fields),
        }
        with self._lock:
            self._events.append(event)

    def list_events(
        self,
        *,
        limit: int = 100,
        event_type: str | None = None,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        if event_type:
            events = [event for event in events if event.get("event") == event_type]
        if request_id:
            events = [event for event in events if event.get("request_id") == request_id]
        return events[-limit:]


recent_events = RecentEventBuffer()
