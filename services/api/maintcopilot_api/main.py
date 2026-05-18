from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from maintcopilot_api.api.error_handlers import register_exception_handlers
from maintcopilot_api.api.routes import auth, chat, health, memory, widgets
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.logging import configure_logging, log_with_context
from maintcopilot_api.infra.minio import MinioClient
from maintcopilot_api.infra.model_client import ModelServerClient
from maintcopilot_api.infra.redis import RedisClient
from maintcopilot_api.infra.tracing import RequestContextMiddleware
from maintcopilot_api.infra.vault import VaultClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings.log_level)

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    vault_client = VaultClient(addr=settings.vault_addr, token=settings.vault_token)
    if settings.require_vault and not vault_client.check_health():
        raise RuntimeError("Vault is required but unreachable.")

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.vault_client = vault_client
    app.state.redis_client = RedisClient(settings.redis_url)
    app.state.minio_client = MinioClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
    )
    app.state.model_client = ModelServerClient(settings.model_server_url)

    log_with_context(logging.getLogger("app.lifecycle"), "info", "api.startup.completed", service=settings.app_name)

    try:
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(widgets.router)
    return app


app = create_app()
