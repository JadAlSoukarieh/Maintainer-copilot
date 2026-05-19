from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from maintcopilot_model_server.domain.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    HealthResponse,
    NerRequest,
    NerResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.infra.config import Settings
from maintcopilot_model_server.services.classifier_service import ClassifierService
from maintcopilot_model_server.services.ner_service import NerService
from maintcopilot_model_server.services.summarizer_service import SummarizerService

router = APIRouter()


def get_settings() -> Settings:
    return Settings()


def get_artifact_loader(settings: Settings = Depends(get_settings)) -> ArtifactLoader:
    return ArtifactLoader(
        settings.classifier_artifact_dir,
        model_dir=settings.classifier_model_dir,
        require_artifacts=settings.classifier_require_artifacts,
        max_length=settings.classifier_max_length,
    )


def get_classifier_service(
    request: Request,
    loader: ArtifactLoader = Depends(get_artifact_loader),
) -> ClassifierService:
    service = getattr(request.app.state, "classifier_service", None)
    if service is None:
        service = ClassifierService(loader)
        request.app.state.classifier_service = service
    return service


def get_ner_service() -> NerService:
    return NerService()


def get_summarizer_service() -> SummarizerService:
    return SummarizerService()


@router.get("/health", response_model=HealthResponse)
def health(loader: ArtifactLoader = Depends(get_artifact_loader)) -> HealthResponse:
    return HealthResponse(status="ok", artifact_dir=str(loader.artifact_dir), artifacts_present=loader.artifacts_present())


@router.post("/classify", response_model=ClassifyResponse)
def classify(
    payload: ClassifyRequest,
    service: ClassifierService = Depends(get_classifier_service),
) -> ClassifyResponse:
    return service.classify(payload)


@router.post("/ner", response_model=NerResponse)
def ner(payload: NerRequest, service: NerService = Depends(get_ner_service)) -> NerResponse:
    return service.extract(payload)


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(
    payload: SummarizeRequest,
    service: SummarizerService = Depends(get_summarizer_service),
) -> SummarizeResponse:
    return service.summarize(payload)
