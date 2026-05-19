from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from maintcopilot_model_server.api.error_handlers import domain_error_handler
from maintcopilot_model_server.domain.errors import ConfigurationError


def test_configuration_error_returns_structured_json() -> None:
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-456"))
    response = asyncio.run(domain_error_handler(request, ConfigurationError("artifact mismatch")))
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "error": {
            "code": "configuration_error",
            "message": "artifact mismatch",
            "request_id": "req-456",
        }
    }
