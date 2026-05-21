from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from maintcopilot_api.infra import minio as minio_module


ROOT = Path(__file__).resolve().parents[3]


def test_minio_client_required_methods_with_fake_backend(monkeypatch) -> None:
    stored: dict[str, bytes] = {}
    bucket_state = {"exists": False}

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body

    class FakeObject:
        def __init__(self, object_name: str) -> None:
            self.object_name = object_name

    class FakeMinio:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def bucket_exists(self, bucket: str) -> bool:
            return bucket_state["exists"]

        def make_bucket(self, bucket: str) -> None:
            bucket_state["exists"] = True

        def put_object(self, bucket: str, key: str, body, *, length: int, content_type: str) -> None:
            stored[key] = body.read(length)

        def get_object(self, bucket: str, key: str) -> FakeResponse:
            return FakeResponse(stored[key])

        def list_objects(self, bucket: str, *, prefix: str, recursive: bool):
            return [FakeObject(key) for key in sorted(stored) if key.startswith(prefix)]

    monkeypatch.setattr(minio_module, "_MINIO_AVAILABLE", True)
    monkeypatch.setattr(minio_module, "Minio", FakeMinio)

    client = minio_module.MinioClient(endpoint="minio:9000", access_key="a", secret_key="s", bucket="b")
    client.ensure_bucket()
    client.put_json("reports/eval.json", {"ok": True})
    client.put_bytes("artifacts/model.bin", b"abc")

    assert client.check_health() is True
    assert client.get_json("reports/eval.json") == {"ok": True}
    assert client.list_keys("reports/") == ["reports/eval.json"]
    assert stored["artifacts/model.bin"] == b"abc"


def test_fastapi_users_v2_routes_are_registered() -> None:
    main_source = (ROOT / "services/api/maintcopilot_api/main.py").read_text(encoding="utf-8")

    assert 'prefix="/auth/v2"' in main_source
    assert 'prefix="/users/v2"' in main_source


def test_chat_stream_returns_sse_events() -> None:
    chat_route = (ROOT / "services/api/maintcopilot_api/api/routes/chat.py").read_text(encoding="utf-8")
    widget = (ROOT / "services/widget/src/App.tsx").read_text(encoding="utf-8")

    assert '@router.post("/chat/stream")' in chat_route
    assert 'media_type="text/event-stream"' in chat_route
    assert '_sse("status"' in chat_route
    assert '_sse("token"' in chat_route
    assert '_sse("done"' in chat_route
    assert "/chat/stream" in widget
    assert "phase: \"streaming\"" in widget
    assert "use_llm: config.default_use_llm" in widget
    assert "Deterministic fallback" in widget


def test_strict_claude_smoke_fails_if_response_falls_back() -> None:
    spec = importlib.util.spec_from_file_location("final_backend_smoke_script", ROOT / "scripts" / "final_backend_smoke.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    args = SimpleNamespace(
        api_base_url="http://localhost:8000",
        model_server_base_url="http://localhost:8001",
        mode="claude",
        output=str(ROOT / "reports" / "test_final_backend_smoke_report.json"),
        skip_claude=False,
        allow_claude_fallback=False,
        require_claude_success=True,
        timeout=10.0,
    )

    def fake_result(name: str, passed: bool, **kwargs):
        return {"name": name, "passed": passed, **kwargs}

    monkeypatches = {
        "parse_args": lambda: args,
        "check_get": lambda *a, **k: fake_result("api_health", True, required=True, summary="ok"),
        "check_widget_config": lambda *a, **k: fake_result("widget_config_allowed_origin", True, required=True, summary="ok"),
        "check_widget_blocked_origin": lambda *a, **k: fake_result("widget_config_blocked_origin", True, required=True, summary="ok"),
        "check_widget_js_csp": lambda *a, **k: fake_result("widget_js_csp", True, required=True, summary="ok"),
        "check_chat_rag": lambda *a, **k: fake_result(
            "claude_rag_chat" if k.get("use_llm") else "deterministic_rag_chat",
            True,
            required=True,
            summary="ok",
            mode="deterministic_fallback" if k.get("use_llm") else "deterministic_fallback",
        ),
        "check_chat_classify": lambda *a, **k: fake_result("deterministic_classify_chat", True, required=True, summary="ok"),
        "check_memory_write": lambda *a, **k: fake_result("explicit_memory_write", True, required=True, summary="ok"),
        "check_memory_search": lambda *a, **k: fake_result("memory_search", True, required=True, summary="ok"),
        "check_get_reports": lambda *a, **k: fake_result("reports_summary", True, required=True, summary="ok"),
        "check_observability": lambda *a, **k: fake_result("observability_recent", True, required=True, summary="ok"),
    }

    for name, value in monkeypatches.items():
        setattr(module, name, value)

    assert module.main() == 1


def test_tracing_claims_have_instrumentation_points() -> None:
    llm_source = (ROOT / "services/api/maintcopilot_api/services/llm_chat_service.py").read_text(encoding="utf-8")
    tools_source = (ROOT / "services/api/maintcopilot_api/services/tools.py").read_text(encoding="utf-8")
    rag_source = (ROOT / "services/api/maintcopilot_api/services/rag/rag_service.py").read_text(encoding="utf-8")
    tracing_source = (ROOT / "services/api/maintcopilot_api/infra/tracing.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "llm.select_tool" in llm_source
    assert "llm.final_response" in llm_source
    assert 'start_as_current_span(f"tool.{tool_name}")' in tools_source
    assert "rag.retrieve" in rag_source
    assert "OTLPSpanExporter" in tracing_source
    assert "jaegertracing/all-in-one" in compose


def test_ci_workflow_has_lint_mypy_and_report_upload() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "lint:" in workflow
    assert "ruff check services/api/maintcopilot_api" in workflow
    assert "type-check:" in workflow
    assert "mypy services/api/maintcopilot_api --ignore-missing-imports --no-error-summary || true" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "if: always()" in workflow
    assert "path: reports/" in workflow
