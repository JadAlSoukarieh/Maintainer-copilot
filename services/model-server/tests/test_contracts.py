from __future__ import annotations

from maintcopilot_model_server.api.routes import classify, ner, summarize
from maintcopilot_model_server.domain.schemas import ClassifyRequest, NerRequest, SummarizeRequest
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.services.classifier_service import ClassifierService
from maintcopilot_model_server.services.ner_service import NerService
from maintcopilot_model_server.services.summarizer_service import SummarizerService


def test_classify_contract() -> None:
    response = classify(ClassifyRequest(text="This bug breaks login."), ClassifierService(ArtifactLoader("/tmp/none")))
    assert response.label == "bug"
    assert response.model_version == "placeholder-classifier-v1"


def test_ner_contract() -> None:
    response = ner(NerRequest(text="Check org/repo and issue #42."), NerService())
    assert any(entity.label == "REPO_REF" for entity in response.entities)


def test_summarize_contract() -> None:
    response = summarize(
        SummarizeRequest(text="Sentence one. Sentence two. Sentence three.", max_sentences=2),
        SummarizerService(),
    )
    assert response.sentences_used == 2
