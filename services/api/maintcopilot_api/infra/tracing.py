from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from maintcopilot_api.infra.redaction import redact

# ---------------------------------------------------------------------------
# Request/trace ID context vars (used throughout the codebase for log correlation)
# ---------------------------------------------------------------------------

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def get_trace_id() -> str:
    return trace_id_var.get()


# ---------------------------------------------------------------------------
# OpenTelemetry setup
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False

_tracer_initialized = False


def configure_tracing(*, service_name: str, otlp_endpoint: str | None = None) -> None:
    """
    Initialise the global OTEL TracerProvider.
    Call once at application startup with the service name and optional OTLP endpoint.
    When *otlp_endpoint* is None, spans are exported to the console only (dev mode).
    """
    global _tracer_initialized
    if not _OTEL_AVAILABLE or _tracer_initialized:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer_initialized = True


def get_tracer(name: str = "maintcopilot") -> Any:
    """Return an OTEL tracer. Falls back to a no-op object when OTEL is unavailable."""
    if not _OTEL_AVAILABLE:
        return _NoOpTracer()
    from opentelemetry import trace
    return trace.get_tracer(name)


class _NoOpSpan:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def set_attribute(self, *_):
        pass

    def record_exception(self, *_):
        pass

    def set_status(self, *_):
        pass


class _NoOpTracer:
    def start_as_current_span(self, name: str, **_):
        return _NoOpSpan()


# ---------------------------------------------------------------------------
# Middleware — sets request/trace IDs, creates root OTEL span per request
# ---------------------------------------------------------------------------

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        trace_id = _extract_trace_id(request.headers.get("traceparent")) or request.headers.get("x-trace-id", str(uuid.uuid4()))

        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        tracer = get_tracer()
        span_name = f"{request.method} {request.url.path}"

        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("request.id", request_id)
            span.set_attribute("trace.id", trace_id)

            try:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
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
            except Exception as exc:
                span.record_exception(exc)
                raise
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
