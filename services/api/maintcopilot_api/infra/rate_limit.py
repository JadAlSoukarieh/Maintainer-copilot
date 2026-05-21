from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi.responses import JSONResponse
from starlette.requests import Request

from maintcopilot_api.infra.auth import JWTManager, TokenError
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import log_with_context
from maintcopilot_api.infra.redis import RedisClient, RedisUnavailableError


@dataclass(slots=True)
class RateLimitPolicy:
    name: str
    max_requests: int


class RateLimitMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        settings = getattr(request.app.state, "settings", None) or Settings()
        if not settings.rate_limit_enabled or settings.rate_limit_backend != "redis":
            await self.app(scope, receive, send)
            return
        if request.url.path.startswith("/health"):
            await self.app(scope, receive, send)
            return

        redis_client = getattr(request.app.state, "redis_client", None)
        if not isinstance(redis_client, RedisClient):
            response = _service_unavailable() if not settings.rate_limit_fail_open else None
            if response is not None:
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        subject = _resolve_subject(request, settings)
        policies = _policies_for_request(request, settings)
        try:
            for policy in policies:
                key = _rate_limit_key(subject=subject, policy=policy, settings=settings)
                current = redis_client.incr_with_window(key, ttl_seconds=settings.rate_limit_window_seconds)
                if current > policy.max_requests:
                    retry_after = redis_client.ttl(key)
                    response = _rate_limited(retry_after, policy.name)
                    await response(scope, receive, send)
                    return
        except RedisUnavailableError as exc:
            if settings.rate_limit_fail_open:
                log_with_context(
                    logging.getLogger("app.rate_limit"),
                    "warning",
                    "rate_limit.backend_unavailable",
                    path=request.url.path,
                    reason=str(exc),
                )
                await self.app(scope, receive, send)
                return
            response = _service_unavailable()
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _resolve_subject(request: Request, settings: Settings) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer ") and settings.jwt_secret:
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            try:
                payload = JWTManager(secret=settings.jwt_secret, expires_minutes=settings.jwt_exp_minutes).decode_token(token)
            except TokenError:
                pass
            else:
                subject = payload.get("sub")
                if isinstance(subject, str) and subject:
                    return f"user:{subject}"

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        client_ip = forwarded.split(",", 1)[0].strip()
        if client_ip:
            return f"ip:{client_ip}"
    client = getattr(request, "client", None)
    if client and client.host:
        return f"ip:{client.host}"
    return "ip:unknown"


def _policies_for_request(request: Request, settings: Settings) -> list[RateLimitPolicy]:
    path = request.url.path
    policies = [RateLimitPolicy(name="global", max_requests=settings.rate_limit_max_requests)]
    if path in {"/chat", "/chat/stream"}:
        policies.append(RateLimitPolicy(name="chat", max_requests=settings.rate_limit_chat_max_requests))
    elif path == "/widget.js" or (path.startswith("/widgets/") and path.endswith("/config")):
        policies.append(RateLimitPolicy(name="widget", max_requests=settings.rate_limit_widget_max_requests))
    return policies


def _rate_limit_key(*, subject: str, policy: RateLimitPolicy, settings: Settings) -> str:
    return f"ratelimit:{policy.name}:{settings.rate_limit_window_seconds}:{subject}"


def _rate_limited(retry_after: int, policy_name: str) -> JSONResponse:
    safe_retry_after = retry_after if retry_after > 0 else 1
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limited", "retry_after_seconds": safe_retry_after},
        headers={"Retry-After": str(safe_retry_after), "X-RateLimit-Policy": policy_name},
    )


def _service_unavailable() -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "rate_limit_backend_unavailable"})
