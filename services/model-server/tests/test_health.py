from __future__ import annotations

import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse

from maintcopilot_model_server.api.routes import health
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.infra.request_context import RequestIdMiddleware


def test_health() -> None:
    response = health(ArtifactLoader("/tmp/does-not-exist", model_dir="/tmp/does-not-exist/model"))
    assert response.status == "ok"
    assert response.artifact_dir == "/tmp/does-not-exist"


def test_response_includes_generated_request_id() -> None:
    middleware = RequestIdMiddleware(app=lambda scope, receive, send: None)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "http_version": "1.1",
            "client": ("test", 1234),
            "server": ("testserver", 80),
        }
    )

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = asyncio.run(middleware.dispatch(request, call_next))
    assert response.headers["x-request-id"]
    assert request.state.request_id == response.headers["x-request-id"]


def test_provided_request_id_is_preserved() -> None:
    middleware = RequestIdMiddleware(app=lambda scope, receive, send: None)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [(b"x-request-id", b"req-abc-123")],
            "query_string": b"",
            "scheme": "http",
            "http_version": "1.1",
            "client": ("test", 1234),
            "server": ("testserver", 80),
        }
    )

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = asyncio.run(middleware.dispatch(request, call_next))
    assert response.headers["x-request-id"] == "req-abc-123"
