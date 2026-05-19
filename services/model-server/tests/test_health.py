from __future__ import annotations

import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse

from maintcopilot_model_server.api.routes import health, ner, summarize
from maintcopilot_model_server.domain.schemas import NerRequest, SummarizeRequest
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.infra.request_context import RequestIdMiddleware
from maintcopilot_model_server.services.ner_service import NerService
from maintcopilot_model_server.services.summarizer_service import SummarizerService


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


def test_all_endpoints_include_x_request_id() -> None:
    middleware = RequestIdMiddleware(app=lambda scope, receive, send: None)

    def make_request() -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/tool",
                "headers": [],
                "query_string": b"",
                "scheme": "http",
                "http_version": "1.1",
                "client": ("test", 1234),
                "server": ("testserver", 80),
            }
        )

    async def run_ner() -> str:
        request = make_request()

        async def call_next(_request: Request) -> JSONResponse:
            payload = ner(NerRequest(title="fs.utimes docs", body="See fs.md and https://nodejs.org"), NerService())
            return JSONResponse(payload.model_dump())

        response = await middleware.dispatch(request, call_next)
        return response.headers["x-request-id"]

    async def run_summarize() -> str:
        request = make_request()

        async def call_next(_request: Request) -> JSONResponse:
            payload = summarize(
                SummarizeRequest(
                    title="Memory leak in https.request",
                    body="Version v6.8.0. Repro: send many requests. Actual: memory grows.",
                    max_bullets=2,
                ),
                SummarizerService(),
            )
            return JSONResponse(payload.model_dump())

        response = await middleware.dispatch(request, call_next)
        return response.headers["x-request-id"]

    ner_request_id = asyncio.run(run_ner())
    summarize_request_id = asyncio.run(run_summarize())
    assert ner_request_id
    assert summarize_request_id
