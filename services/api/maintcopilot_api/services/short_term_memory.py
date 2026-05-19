from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from maintcopilot_api.infra.redaction import redact
from maintcopilot_api.infra.redis import RedisClient


class ShortTermMemoryStore(Protocol):
    def check_available(self) -> None: ...

    def append(self, *, conversation_id: str, event: dict[str, Any]) -> None: ...


class InMemoryShortTermMemoryStore:
    def __init__(self) -> None:
        self.events: dict[str, list[dict[str, Any]]] = {}

    def check_available(self) -> None:
        return None

    def append(self, *, conversation_id: str, event: dict[str, Any]) -> None:
        self.events.setdefault(conversation_id, []).append(_memory_event(event))


class RedisShortTermMemoryStore:
    def __init__(self, redis_client: RedisClient, *, ttl_seconds: int) -> None:
        self._redis_client = redis_client
        self._ttl_seconds = ttl_seconds

    def check_available(self) -> None:
        self._redis_client.check_available()

    def append(self, *, conversation_id: str, event: dict[str, Any]) -> None:
        self._redis_client.append_json_with_ttl(
            f"chat:short_term:{conversation_id}",
            _memory_event(event),
            self._ttl_seconds,
        )


def _memory_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    return redact(payload)
