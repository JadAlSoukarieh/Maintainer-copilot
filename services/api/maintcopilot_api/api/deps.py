from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from maintcopilot_api.infra.config import Settings
from maintcopilot_api.services.chat_service import ChatService
from maintcopilot_api.services.health_service import HealthService
from maintcopilot_api.services.memory_service import MemoryService
from maintcopilot_api.services.widget_service import WidgetService
from maintcopilot_api.repositories.memory_repository import MemoryRepository
from maintcopilot_api.repositories.widget_repository import WidgetRepository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_chat_service(request: Request) -> ChatService:
    return ChatService(model_client=request.app.state.model_client)


def get_memory_service(session: Session = Depends(get_db_session)) -> MemoryService:
    return MemoryService(repository=MemoryRepository(session=session), session=session)


def get_widget_service(session: Session = Depends(get_db_session)) -> WidgetService:
    return WidgetService(repository=WidgetRepository(session=session))


def get_health_service(request: Request) -> HealthService:
    return HealthService(
        session_factory=request.app.state.session_factory,
        vault_client=request.app.state.vault_client,
        require_vault=request.app.state.settings.require_vault,
    )
