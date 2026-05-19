from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from maintcopilot_model_server.api.error_handlers import register_exception_handlers
from maintcopilot_model_server.api.routes import router
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.infra.config import Settings
from maintcopilot_model_server.infra.request_context import RequestIdMiddleware
from maintcopilot_model_server.services.classifier_service import ClassifierService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    loader = ArtifactLoader(
        settings.classifier_artifact_dir,
        model_dir=settings.classifier_model_dir,
        require_artifacts=settings.classifier_require_artifacts,
        max_length=settings.classifier_max_length,
    )
    app.state.artifact_loader = loader
    app.state.classifier_service = ClassifierService(loader)
    if settings.classifier_require_artifacts:
        loader.load_classifier_artifacts()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot Model Server", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
