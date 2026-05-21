from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]


def test_widget_snippet_generation() -> None:
    module = _load_module("api_client")
    snippet = module.build_widget_snippet(
        api_base_url="http://localhost:8000",
        widget_id="demo-widget",
        widget_url="http://localhost:5173",
    )

    assert 'src="http://localhost:8000/widget.js?public_widget_id=demo-widget"' in snippet
    assert 'data-widget-id="demo-widget"' in snippet
    assert 'data-widget-url="http://localhost:5173"' in snippet


def test_api_client_auth_header_construction(monkeypatch) -> None:
    module = _load_module("api_client")
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"ok": True}

    def fake_request(method, url, headers, json, timeout):
        captured.update({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(module.requests, "request", fake_request)
    client = module.ApiClient("http://api:8000", token="jwt-token")
    response = client.get("/health")

    assert response == {"ok": True}
    assert captured["headers"]["authorization"] == "Bearer jwt-token"


def test_session_state_initialization_defaults() -> None:
    module = _load_module("session_state")
    fake_state = {}
    module.st = SimpleNamespace(session_state=fake_state)

    module.init_state()

    assert fake_state["api_base_url"] == "http://api:8000"
    assert fake_state["use_llm"] is True
    assert fake_state["messages"] == []
    assert fake_state["issue_title"] == ""


def test_session_state_respects_llm_disabled_env(monkeypatch) -> None:
    monkeypatch.setenv("API_CHAT_LLM_ENABLED", "false")
    module = _load_module("session_state")
    fake_state = {}
    module.st = SimpleNamespace(session_state=fake_state)

    module.init_state()

    assert fake_state["use_llm"] is False


def test_citation_formatting_helper() -> None:
    module = _load_module("components")
    formatted = module.format_citation(
        {
            "title": "stream.pipeline()",
            "source_type": "doc",
            "chunk_id": "doc-stream-001",
            "text_excerpt": "stream.pipeline() will call stream.destroy(err) on all streams after an error.",
            "url": "https://nodejs.org/api/stream.html",
        }
    )

    assert formatted["title"] == "stream.pipeline()"
    assert formatted["source_type"] == "Docs"
    assert formatted["chunk_id"] == "doc-stream-001"
    assert len(formatted["excerpt"]) <= 300


def test_report_metric_formatting_helper() -> None:
    module = _load_module("components")

    assert module.format_report_metric(0.711572, digits=3) == "0.712"
    assert module.format_report_metric(None) == "n/a"


def _load_module(name: str):
    streamlit_module = ModuleType("streamlit")
    streamlit_module.session_state = {}
    streamlit_module.markdown = lambda *args, **kwargs: None
    streamlit_module.code = lambda *args, **kwargs: None
    streamlit_module.text_area = lambda *args, **kwargs: None
    streamlit_module.info = lambda *args, **kwargs: None
    sys.modules.setdefault("streamlit", streamlit_module)
    chatbot_dir = str(ROOT / "services" / "chatbot")
    if chatbot_dir not in sys.path:
        sys.path.insert(0, chatbot_dir)

    path = ROOT / "services" / "chatbot" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"chatbot_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
