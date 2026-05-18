from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.errors import AuthenticationError, ForbiddenError
from maintcopilot_api.infra.auth import JWTManager, PasswordHasher, TokenError
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.repositories.auth_repository import AuthRepository
from maintcopilot_api.repositories.memory_repository import MemoryRepository
from maintcopilot_api.repositories.widget_repository import WidgetRepository
from maintcopilot_api.services.auth_service import AuthService
from maintcopilot_api.services.chat_service import ChatService
from maintcopilot_api.services.health_service import HealthService
from maintcopilot_api.services.memory_service import MemoryService
from maintcopilot_api.services.widget_service import WidgetService

bearer_scheme = HTTPBearer(auto_error=False)


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


def get_auth_service(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    jwt_secret = settings.jwt_secret
    if not jwt_secret:
        raise AuthenticationError("JWT secret is not configured.")
    return AuthService(
        repository=AuthRepository(session=session),
        audit_repository=AuditRepository(session=session),
        session=session,
        password_hasher=PasswordHasher(),
        jwt_manager=JWTManager(secret=jwt_secret, expires_minutes=settings.jwt_exp_minutes),
        settings=settings,
    )


def get_memory_service(session: Session = Depends(get_db_session)) -> MemoryService:
    return MemoryService(repository=MemoryRepository(session=session), session=session)


def get_widget_service(session: Session = Depends(get_db_session)) -> WidgetService:
    return WidgetService(
        repository=WidgetRepository(session=session),
        audit_repository=AuditRepository(session=session),
        session=session,
    )


def get_health_service(request: Request) -> HealthService:
    return HealthService(
        session_factory=request.app.state.session_factory,
        vault_client=request.app.state.vault_client,
        require_vault=request.app.state.settings.require_vault,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication credentials were not provided.")
    try:
        return auth_service.get_current_user(credentials.credentials)
    except TokenError as exc:
        raise AuthenticationError(str(exc)) from exc


def require_admin(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    if current_user.role != "admin":
        raise ForbiddenError("Admin access is required.")
    return current_user
