from __future__ import annotations

from typing import Any

import httpx


class ModelClientError(RuntimeError):
    pass


class ModelServerClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def preview_classification(self, text: str) -> str:
        lowered = text.lower()
        if "bug" in lowered or "error" in lowered:
            return "bug"
        if "feature" in lowered or "enhancement" in lowered:
            return "feature"
        if "doc" in lowered or "readme" in lowered:
            return "docs"
        return "question"

    def classify_issue(self, *, title: str, body: str) -> dict[str, Any]:
        return self._post("/classify", {"title": title, "body": body})

    def extract_entities(self, *, title: str, body: str) -> dict[str, Any]:
        return self._post("/ner", {"title": title, "body": body})

    def summarize_thread(self, *, title: str, body: str, max_bullets: int = 5) -> dict[str, Any]:
        return self._post("/summarize", {"title": title, "body": body, "max_bullets": max_bullets})

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise ModelClientError("Model-server request failed.") from exc
        if not isinstance(data, dict):
            raise ModelClientError("Model-server returned an invalid response.")
        return data
