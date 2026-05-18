from __future__ import annotations

import re

REDACTION_TOKEN = "[REDACTED]"


def redact(value: str) -> str:
    patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]+\b"),
        re.compile(r"\bghp_[A-Za-z0-9]+\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"),
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ]
    redacted = value
    for pattern in patterns:
        redacted = pattern.sub(REDACTION_TOKEN, redacted)
    redacted = re.sub(r"(?i)\b(password|passwd|pwd|secret)\s*=\s*([^\s,;]+)", rf"\1={REDACTION_TOKEN}", redacted)
    return redacted

