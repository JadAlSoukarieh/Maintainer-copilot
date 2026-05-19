from __future__ import annotations

import json
import re


PROMPT_VERSION = "llm-baseline-v1"
VALID_LABELS = ("bug", "feature", "docs", "question")

_LABEL_ALIASES = {
    "bug": "bug",
    "bugs": "bug",
    "defect": "bug",
    "feature": "feature",
    "enhancement": "feature",
    "feature_request": "feature",
    "feature request": "feature",
    "docs": "docs",
    "doc": "docs",
    "documentation": "docs",
    "question": "question",
    "help": "question",
    "support": "question",
}


class InvalidLLMBaselineOutputError(ValueError):
    pass


def strip_code_fences(value: str) -> str:
    text = value.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()
    return text


def normalize_label(value: str) -> str | None:
    normalized = value.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return _LABEL_ALIASES.get(normalized)


def parse_label_response(raw_output: str) -> str:
    candidate = strip_code_fences(raw_output)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise InvalidLLMBaselineOutputError("Claude output was not valid JSON.") from exc

    if not isinstance(payload, dict) or set(payload.keys()) != {"label"}:
        raise InvalidLLMBaselineOutputError("Claude output must be a JSON object with only a label field.")

    label_value = payload.get("label")
    if not isinstance(label_value, str):
        raise InvalidLLMBaselineOutputError("Claude label must be a string.")

    normalized_label = normalize_label(label_value)
    if normalized_label not in VALID_LABELS:
        raise InvalidLLMBaselineOutputError("Claude label could not be normalized to a supported class.")

    return normalized_label
