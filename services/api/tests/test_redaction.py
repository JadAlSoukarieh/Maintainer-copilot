from __future__ import annotations

from maintcopilot_api.infra.redaction import redact


def test_redaction_masks_fake_secrets() -> None:
    sample = {
        "openai": "sk-test123456",
        "anthropic": "sk-ant-test-secret-value",
        "github": "ghp_abcd1234token",
        "fine_grained": "github_pat_123456_token_value",
        "bearer": "Bearer token-value-123",
        "email": "maintainer@example.com",
        "password": "password=hunter2",
    }

    redacted = redact(sample)
    rendered = str(redacted)

    assert "sk-test123456" not in rendered
    assert "sk-ant-test-secret-value" not in rendered
    assert "ghp_abcd1234token" not in rendered
    assert "github_pat_123456_token_value" not in rendered
    assert "token-value-123" not in rendered
    assert "maintainer@example.com" not in rendered
    assert "hunter2" not in rendered
    assert rendered.count("[REDACTED]") >= 5
