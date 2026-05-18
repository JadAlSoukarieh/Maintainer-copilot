from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from maintcopilot_api.api.error_handlers import domain_error_handler
from maintcopilot_api.domain.errors import DomainError


@pytest.mark.anyio
async def test_domain_error_returns_structured_json() -> None:
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-123"))
    response = await domain_error_handler(request, DomainError("boom", code="boom_error", status_code=409))

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error": {
            "code": "boom_error",
            "message": "boom",
            "request_id": "req-123",
        }
    }
