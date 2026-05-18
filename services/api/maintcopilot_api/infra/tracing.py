from __future__ import annotations

import contextvars
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from maintcopilot_api.infra.redaction import redact

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def get_trace_id() -> str:
    return trace_id_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        trace_id = _extract_trace_id(request.headers.get("traceparent")) or request.headers.get("x-trace-id", str(uuid.uuid4()))

        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            response.headers["x-trace-id"] = trace_id
            logging.getLogger("app.request").info(
                "request.completed",
                extra={
                    "event_fields": redact(
                        {
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                        }
                    )
                },
            )
            return response
        finally:
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)


def _extract_trace_id(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    parts = traceparent.split("-")
    if len(parts) >= 4 and parts[1]:
        return parts[1]
    return None
