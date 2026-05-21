from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from maintcopilot_api.api.error_handlers import register_exception_handlers
from maintcopilot_api.api.routes import auth, chat, health, memory, observability, rag, reports, widgets
from maintcopilot_api.infra.fastapi_users_setup import FUUserCreate, FUUserRead, FUUserUpdate, auth_backend, fastapi_users
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.embeddings import LocalSentenceTransformerEmbedder
from maintcopilot_api.infra.logging import configure_logging, log_with_context
from maintcopilot_api.infra.minio import MinioClient
from maintcopilot_api.infra.model_client import ModelServerClient
from maintcopilot_api.infra.rate_limit import RateLimitMiddleware
from maintcopilot_api.infra.redis import RedisClient
from maintcopilot_api.infra.startup import init_minio, validate_startup
from maintcopilot_api.infra.tracing import RequestContextMiddleware, configure_tracing
from maintcopilot_api.infra.vault import VaultClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings.log_level)
    configure_tracing(
        service_name=settings.app_name,
        otlp_endpoint=settings.otel_exporter_endpoint,
    )

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    vault_client = VaultClient(addr=settings.vault_addr, token=settings.vault_token)
    startup_diagnostics = validate_startup(settings, vault_client, repo_root=_repo_root())

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.vault_client = vault_client
    app.state.redis_client = RedisClient(settings.redis_url)
    minio_client = MinioClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
    )
    app.state.minio_client = minio_client
    init_minio(minio_client, repo_root=_repo_root(), warnings=startup_diagnostics.setdefault("warnings", []))
    app.state.model_client = ModelServerClient(settings.model_server_url)
    app.state.memory_embedder = LocalSentenceTransformerEmbedder(
        model_name=settings.memory_embedding_model,
        local_files_only=True,
    )
    app.state.startup_diagnostics = startup_diagnostics

    log_with_context(logging.getLogger("app.lifecycle"), "info", "api.startup.completed", service=settings.app_name)

    try:
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8090",
            "http://127.0.0.1:8090",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    register_exception_handlers(app)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(widgets.router)
    app.include_router(rag.router)
    app.include_router(reports.router)
    app.include_router(observability.router)
    # fastapi-users routers at /auth/v2 (complements the custom invite-flow routes at /auth)
    app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/v2", tags=["auth-v2"])
    app.include_router(fastapi_users.get_register_router(FUUserRead, FUUserCreate), prefix="/auth/v2", tags=["auth-v2"])
    app.include_router(fastapi_users.get_users_router(FUUserRead, FUUserUpdate), prefix="/users/v2", tags=["users-v2"])
    return app


app = create_app()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
