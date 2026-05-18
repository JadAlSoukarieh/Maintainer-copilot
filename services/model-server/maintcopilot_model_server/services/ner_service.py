from __future__ import annotations

from maintcopilot_model_server.domain.schemas import Entity, NerRequest, NerResponse


class NerService:
    def extract(self, payload: NerRequest) -> NerResponse:
        entities: list[Entity] = []
        for token in payload.text.split():
            cleaned = token.strip(".,:;()[]{}")
            if cleaned.startswith("#") and len(cleaned) > 1:
                start = payload.text.find(cleaned)
                entities.append(Entity(text=cleaned, label="ISSUE_REF", start=start, end=start + len(cleaned)))
            elif "/" in cleaned and cleaned.count("/") == 1:
                start = payload.text.find(cleaned)
                entities.append(Entity(text=cleaned, label="REPO_REF", start=start, end=start + len(cleaned)))
        return NerResponse(entities=entities, model_version="placeholder-ner-v1")
