from __future__ import annotations

from maintcopilot_api.api.routes.health import health


def test_health() -> None:
    assert health() == {"status": "ok"}
