from __future__ import annotations


class ModelServerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def preview_classification(self, text: str) -> str:
        lowered = text.lower()
        if "bug" in lowered or "error" in lowered:
            return "bug"
        if "feature" in lowered or "enhancement" in lowered:
            return "feature"
        if "doc" in lowered or "readme" in lowered:
            return "docs"
        return "question"

