from __future__ import annotations

import re

from maintcopilot_model_server.domain.schemas import SummarizeRequest, SummarizeResponse


class SummarizerService:
    PRIORITY_PATTERNS = [
        re.compile(r"\b(repro|reproduce|steps|step \d+|expected|actual|error|exception|crash|regression|leak)\b", re.IGNORECASE),
        re.compile(r"\b(version|platform|ubuntu|linux|macos|windows|xcode|subsystem)\b", re.IGNORECASE),
    ]

    def summarize(self, payload: SummarizeRequest) -> SummarizeResponse:
        title = payload.title.strip()
        body = payload.body.strip()
        sentences = self._split_sentences(body)
        scored = self._score_sentences(sentences)

        bullets: list[str] = [title]
        seen = {title}
        for sentence in scored:
            normalized = sentence.strip()
            if not normalized or normalized in seen:
                continue
            bullets.append(normalized)
            seen.add(normalized)
            if len(bullets) >= payload.max_bullets:
                break

        bullets = bullets[: payload.max_bullets]
        summary = " ".join(bullets[: min(len(bullets), 3)])
        if len(summary) > 500:
            summary = summary[:497].rstrip() + "..."
        return SummarizeResponse(summary=summary, bullets=bullets, method="extractive")

    @staticmethod
    def _split_sentences(body: str) -> list[str]:
        cleaned = body.replace("\r", "\n")
        chunks = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        return [chunk.strip(" -*\t") for chunk in chunks if chunk.strip(" -*\t")]

    def _score_sentences(self, sentences: list[str]) -> list[str]:
        scored: list[tuple[int, int, str]] = []
        for index, sentence in enumerate(sentences):
            score = 0
            if len(sentence) < 20:
                continue
            if len(sentence) <= 220:
                score += 1
            for pattern_index, pattern in enumerate(self.PRIORITY_PATTERNS, start=1):
                if pattern.search(sentence):
                    score += 4 - pattern_index
            if sentence.lower().startswith(("version", "platform", "subsystem")):
                score += 2
            scored.append((score, -index, sentence))
        scored.sort(reverse=True)
        return [sentence for _, _, sentence in scored]
