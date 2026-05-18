from __future__ import annotations

from maintcopilot_model_server.domain.schemas import ClassifyRequest, ClassifyResponse
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader


class ClassifierService:
    def __init__(self, loader: ArtifactLoader) -> None:
        self._loader = loader

    def classify(self, payload: ClassifyRequest) -> ClassifyResponse:
        lowered = payload.text.lower()
        label = "question"
        if "bug" in lowered or "error" in lowered:
            label = "bug"
        elif "feature" in lowered or "enhancement" in lowered:
            label = "feature"
        elif "doc" in lowered or "readme" in lowered:
            label = "docs"

        scores = {
            "bug": 0.05,
            "feature": 0.05,
            "docs": 0.05,
            "question": 0.05,
        }
        scores[label] = 0.85
        return ClassifyResponse(
            label=label,
            confidence=scores[label],
            scores=scores,
            model_version=self._loader.model_version(),
        )
