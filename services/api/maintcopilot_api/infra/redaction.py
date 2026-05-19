from __future__ import annotations

import re
from typing import Any

REDACTION_TOKEN = "[REDACTED]"

PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]+\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]+\b"),
    re.compile(r"\bghp_[A-Za-z0-9]+\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?i)\b(password|passwd|pwd|secret)\s*=\s*([^\s,;]+)"),
]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if not isinstance(value, str):
        return value

    redacted = value
    for pattern in PATTERNS[:-1]:
        redacted = pattern.sub(REDACTION_TOKEN, redacted)
    redacted = PATTERNS[-1].sub(lambda match: f"{match.group(1)}={REDACTION_TOKEN}", redacted)
    return redacted
