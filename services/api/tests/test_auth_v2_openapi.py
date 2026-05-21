from __future__ import annotations

from maintcopilot_api.main import create_app


def test_fastapi_users_routes_are_registered_in_app() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}

    assert any(path.startswith("/auth/v2") for path in paths)
    assert any(path.startswith("/users/v2") for path in paths)
    assert any(path.startswith("/auth") for path in paths)


def test_openapi_includes_auth_v2_and_users_v2_routes() -> None:
    app = create_app()
    schema = app.openapi()
    paths = schema["paths"]

    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/auth/v2/login" in paths
    assert "/auth/v2/register" in paths
    assert "/users/v2/me" in paths
