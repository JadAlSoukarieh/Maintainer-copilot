from __future__ import annotations

import json
from typing import Any


class RedisUnavailableError(RuntimeError):
    pass


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self._client: Any | None = None

    def append_json_with_ttl(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        client = self._get_client()
        try:
            pipe = client.pipeline()
            pipe.rpush(key, json.dumps(payload, default=str))
            pipe.expire(key, ttl_seconds)
            pipe.execute()
        except Exception as exc:
            raise RedisUnavailableError("Redis short-term memory is unavailable.") from exc

    def list_json(self, key: str, *, limit: int = 100) -> list[dict[str, Any]]:
        client = self._get_client()
        try:
            raw_items = client.lrange(key, max(-limit, 0 - limit), -1)
        except Exception as exc:
            raise RedisUnavailableError("Redis short-term memory is unavailable.") from exc
        items: list[dict[str, Any]] = []
        for item in raw_items:
            try:
                payload = json.loads(item)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                items.append(payload)
        return items

    def check_available(self) -> None:
        client = self._get_client()
        try:
            client.ping()
        except Exception as exc:
            raise RedisUnavailableError("Redis short-term memory is unavailable.") from exc

    def incr_with_window(self, key: str, *, ttl_seconds: int) -> int:
        client = self._get_client()
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            current, ttl = pipe.execute()
            if ttl in (-2, -1):
                client.expire(key, ttl_seconds)
            return int(current)
        except Exception as exc:
            raise RedisUnavailableError("Redis is unavailable.") from exc

    def ttl(self, key: str) -> int:
        client = self._get_client()
        try:
            return int(client.ttl(key))
        except Exception as exc:
            raise RedisUnavailableError("Redis is unavailable.") from exc

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis
        except ImportError as exc:
            raise RedisUnavailableError("The redis package is required for Redis short-term memory.") from exc
        self._client = redis.Redis.from_url(self.url, decode_responses=True)
        return self._client
