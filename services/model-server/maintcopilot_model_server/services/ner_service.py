from __future__ import annotations

import re

from maintcopilot_model_server.domain.schemas import Entity, NerRequest, NerResponse


class NerService:
    MAX_ENTITIES = 50
    TYPE_PRIORITY = {
        "url": 0,
        "file_path": 1,
        "error_code": 2,
        "cli_flag": 3,
        "version": 4,
        "function": 5,
        "module": 6,
        "code_identifier": 7,
    }

    PATTERNS = [
        ("url", re.compile(r"https?://[^\s)>\]]+")),
        ("file_path", re.compile(r"(?<![\w-])(?:[A-Za-z]:\\|/)?(?:[\w.\-]+/)+[\w.\-]+")),
        ("error_code", re.compile(r"\b(?:E[A-Z0-9]{2,}|ERR_[A-Z0-9_]+)\b")),
        ("cli_flag", re.compile(r"(?<!\w)--[a-z0-9][a-z0-9-]*")),
        ("version", re.compile(r"\bv\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\b")),
        ("function", re.compile(r"\b(?:[A-Za-z_]\w*(?:::[A-Za-z_]\w*)+|[A-Za-z_]\w*(?:\.[A-Za-z_]\w+)+)(?:\(\))?")),
        ("module", re.compile(r"(?:(?<=require\(['\"])|(?<=from ['\"])|(?<=import ['\"]))[@A-Za-z0-9_.-]+(?:/[@A-Za-z0-9_.-]+)*")),
        ("code_identifier", re.compile(r"`([^`]+)`|\"([A-Za-z_][\w.:/-]*)\"|'([A-Za-z_][\w.:/-]*)'")),
    ]

    def extract(self, payload: NerRequest) -> NerResponse:
        text = self._combined_text(payload)
        matches: list[Entity] = []
        seen_by_type_text: set[tuple[str, str]] = set()

        for entity_type, pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                entity_text, start, end = self._extract_match(match, entity_type)
                if not entity_text:
                    continue
                entity_text = entity_text.strip(" \t\r\n.,:;()[]{}")
                if len(entity_text) < 2:
                    continue
                key = (entity_type, entity_text)
                if key in seen_by_type_text:
                    continue
                candidate = Entity(text=entity_text, type=entity_type, start=start, end=start + len(entity_text))
                if self._should_skip_candidate(candidate, matches):
                    continue
                self._drop_lower_priority_overlaps(candidate, matches)
                matches.append(candidate)
                seen_by_type_text.add(key)

        entities = sorted(matches, key=lambda item: (item.start, item.end))[: self.MAX_ENTITIES]
        return NerResponse(entities=entities)

    @staticmethod
    def _combined_text(payload: NerRequest) -> str:
        return f"{payload.title}\n\n{payload.body}".strip()

    @staticmethod
    def _extract_match(match: re.Match[str], entity_type: str) -> tuple[str, int, int]:
        if entity_type != "code_identifier":
            start, end = match.span()
            return match.group(0), start, end
        for index in range(1, 4):
            value = match.group(index)
            if value:
                start, end = match.span(index)
                return value, start, end
        return "", 0, 0

    def _should_skip_candidate(self, candidate: Entity, matches: list[Entity]) -> bool:
        for existing in matches:
            if not self._overlaps(candidate, existing):
                continue
            if self.TYPE_PRIORITY[existing.type] <= self.TYPE_PRIORITY[candidate.type]:
                return True
        return False

    def _drop_lower_priority_overlaps(self, candidate: Entity, matches: list[Entity]) -> None:
        matches[:] = [
            existing
            for existing in matches
            if not self._overlaps(candidate, existing)
            or self.TYPE_PRIORITY[existing.type] <= self.TYPE_PRIORITY[candidate.type]
        ]

    @staticmethod
    def _overlaps(left: Entity, right: Entity) -> bool:
        return left.start < right.end and right.start < left.end
