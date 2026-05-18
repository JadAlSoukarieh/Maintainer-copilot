from __future__ import annotations

from maintcopilot_model_server.api.routes import health
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader


def test_health() -> None:
    response = health(ArtifactLoader("/tmp/does-not-exist"))
    assert response.status == "ok"
    assert response.artifact_dir == "/tmp/does-not-exist"
