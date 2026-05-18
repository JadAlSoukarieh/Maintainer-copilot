from __future__ import annotations

import re

from maintcopilot_model_server.domain.schemas import SummarizeRequest, SummarizeResponse


class SummarizerService:
    def summarize(self, payload: SummarizeRequest) -> SummarizeResponse:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", payload.text.strip()) if item.strip()]
        selected = sentences[: payload.max_sentences]
        summary = " ".join(selected) if selected else payload.text[:160]
        return SummarizeResponse(
            summary=summary,
            sentences_used=len(selected) if selected else 1,
            metadata={"strategy": "leading_sentences", "placeholder": True},
        )
