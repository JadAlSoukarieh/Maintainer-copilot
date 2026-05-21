from __future__ import annotations

from types import SimpleNamespace

import pytest

from maintcopilot_api.infra.auth import JWTManager
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.rate_limit import RateLimitMiddleware
from maintcopilot_api.infra.redis import RedisClient


class FakePipeline:
    def __init__(self, backend: "FakeRedisBackend") -> None:
        self.backend = backend
        self.key: str | None = None

    def incr(self, key: str) -> None:
        self.key = key

    def ttl(self, key: str) -> None:
        self.key = key

    def execute(self) -> list[int]:
        assert self.key is not None
        current = self.backend.counters.get(self.key, 0) + 1
        self.backend.counters[self.key] = current
        ttl = self.backend.ttls.get(self.key, -2)
        return [current, ttl]


class FakeRedisBackend:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttls[key] = ttl_seconds

    def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)


class FailingRedisBackend:
    def pipeline(self):
        raise RuntimeError("redis down")


async def _run_request(
    *,
    path: str,
    settings: Settings,
    redis_backend,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, bytes]:
    response_parts: dict[str, object] = {}

    async def app(scope, receive, send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok": true}', "more_body": False})

    redis_client = RedisClient("redis://test/0")
    redis_client._client = redis_backend
    middleware = RateLimitMiddleware(app)
    scope = {
        "type": "http",
        "method": "POST" if path == "/chat" else "GET",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "server": ("testserver", 80),
        "app": SimpleNamespace(state=SimpleNamespace(settings=settings, redis_client=redis_client)),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            response_parts["status"] = message["status"]
        elif message["type"] == "http.response.body":
            response_parts["body"] = message.get("body", b"")

    await middleware(scope, receive, send)
    return int(response_parts["status"]), bytes(response_parts.get("body", b""))


@pytest.mark.anyio
async def test_rate_limit_disabled_by_default_allows_requests() -> None:
    status1, _ = await _run_request(path="/plain", settings=Settings(require_vault=False), redis_backend=FakeRedisBackend())
    status2, _ = await _run_request(path="/plain", settings=Settings(require_vault=False), redis_backend=FakeRedisBackend())

    assert status1 == 200
    assert status2 == 200


@pytest.mark.anyio
async def test_chat_limit_returns_429_after_threshold() -> None:
    settings = Settings(
        require_vault=False,
        rate_limit_enabled=True,
        rate_limit_max_requests=100,
        rate_limit_chat_max_requests=1,
        jwt_secret="test-secret",
    )
    backend = FakeRedisBackend()
    token, _ = JWTManager(secret="test-secret", expires_minutes=60).create_token(
        subject="user-123",
        email="u@example.com",
        role="user",
        is_active=True,
    )
    headers = [(b"authorization", f"Bearer {token}".encode("utf-8"))]

    first = await _run_request(path="/chat", settings=settings, redis_backend=backend, headers=headers)
    second = await _run_request(path="/chat", settings=settings, redis_backend=backend, headers=headers)

    assert first[0] == 200
    assert second[0] == 429
    assert b"rate_limited" in second[1]


@pytest.mark.anyio
async def test_widget_limit_is_separate_from_global_limit() -> None:
    settings = Settings(
        require_vault=False,
        rate_limit_enabled=True,
        rate_limit_max_requests=100,
        rate_limit_widget_max_requests=1,
    )
    backend = FakeRedisBackend()

    first = await _run_request(path="/widget.js", settings=settings, redis_backend=backend)
    second = await _run_request(path="/widget.js", settings=settings, redis_backend=backend)

    assert first[0] == 200
    assert second[0] == 429


@pytest.mark.anyio
async def test_health_is_not_rate_limited() -> None:
    settings = Settings(require_vault=False, rate_limit_enabled=True, rate_limit_max_requests=1)
    backend = FakeRedisBackend()

    first = await _run_request(path="/health", settings=settings, redis_backend=backend)
    second = await _run_request(path="/health", settings=settings, redis_backend=backend)

    assert first[0] == 200
    assert second[0] == 200


@pytest.mark.anyio
async def test_redis_failure_returns_503_when_fail_closed() -> None:
    settings = Settings(require_vault=False, rate_limit_enabled=True, rate_limit_fail_open=False)

    status, body = await _run_request(path="/plain", settings=settings, redis_backend=FailingRedisBackend())

    assert status == 503
    assert b"rate_limit_backend_unavailable" in body


@pytest.mark.anyio
async def test_redis_failure_allows_request_when_fail_open() -> None:
    settings = Settings(require_vault=False, rate_limit_enabled=True, rate_limit_fail_open=True)

    status, _ = await _run_request(path="/plain", settings=settings, redis_backend=FailingRedisBackend())

    assert status == 200
