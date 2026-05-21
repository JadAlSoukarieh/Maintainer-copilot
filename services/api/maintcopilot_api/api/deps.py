from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from maintcopilot_api.domain.auth import UserRead
from maintcopilot_api.domain.errors import AuthenticationError, DependencyUnavailableError, ForbiddenError
from maintcopilot_api.infra.auth import JWTManager, PasswordHasher, TokenError
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.infra.embeddings import LocalSentenceTransformerEmbedder
from maintcopilot_api.infra.redis import RedisUnavailableError
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.repositories.auth_repository import AuthRepository
from maintcopilot_api.repositories.memory_repository import MemoryRepository
from maintcopilot_api.repositories.widget_repository import WidgetRepository
from maintcopilot_api.services.auth_service import AuthService
from maintcopilot_api.services.chat_service import ChatService
from maintcopilot_api.services.health_service import HealthService
from maintcopilot_api.services.llm_chat_service import LLMChatService
from maintcopilot_api.services.memory_service import MemoryService
from maintcopilot_api.services.rag.rag_service import RagService
from maintcopilot_api.services.short_term_memory import InMemoryShortTermMemoryStore, RedisShortTermMemoryStore, ShortTermMemoryStore
from maintcopilot_api.services.tools import ToolExecutor
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


def get_rag_service(settings: Settings = Depends(get_settings)) -> RagService:
    return RagService(
        corpus_path=_resolve_repo_path(settings.rag_corpus_path),
        embedding_index_dir=_resolve_repo_path(settings.rag_embedding_index_dir),
        reranker_model_path=_resolve_repo_path(settings.rag_reranker_model_path),
        rerank_top_n=settings.rag_rerank_top_n,
    )


def get_chat_service(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    rag_service: RagService = Depends(get_rag_service),
) -> ChatService:
    memory_service = MemoryService(
        repository=MemoryRepository(session=session),
        session=session,
        settings=settings,
        embedder=request.app.state.memory_embedder,
    )
    audit_repository = AuditRepository(session=session)
    tool_executor = ToolExecutor(
        model_client=request.app.state.model_client,
        rag_service=rag_service,
        memory_service=memory_service,
        audit_repository=audit_repository,
        session=session,
    )
    llm_service = None
    if settings.chat_llm_enabled:
        llm_service = LLMChatService(
            settings=settings,
            vault_client=request.app.state.vault_client,
            prompt_path=_resolve_repo_path("prompts/chat_system.md"),
        )
    return ChatService(
        tool_executor=tool_executor,
        short_term_memory=get_short_term_memory_store(request, settings),
        settings=settings,
        llm_chat_service=llm_service,
    )


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


def get_memory_service(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> MemoryService:
    return MemoryService(
        repository=MemoryRepository(session=session),
        session=session,
        settings=settings,
        embedder=request.app.state.memory_embedder,
    )


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


def get_memory_embedder(settings: Settings) -> LocalSentenceTransformerEmbedder:
    return LocalSentenceTransformerEmbedder(model_name=settings.memory_embedding_model, local_files_only=True)


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


def get_chat_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db_session),
) -> UserRead | None:
    if settings.auth_optional_for_dev and credentials is None:
        return None
    auth_service = get_auth_service(request, session, settings)
    return get_current_user(credentials, auth_service)


def _resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    repo_root = Path(__file__).resolve().parents[4]
    return (repo_root / candidate).resolve()


def get_short_term_memory_store(request: Request, settings: Settings) -> ShortTermMemoryStore:
    if settings.allow_in_memory_memory:
        store = getattr(request.app.state, "in_memory_short_term_memory", None)
        if store is None:
            store = InMemoryShortTermMemoryStore()
            request.app.state.in_memory_short_term_memory = store
        return store

    store = RedisShortTermMemoryStore(
        request.app.state.redis_client,
        ttl_seconds=settings.short_term_memory_ttl_seconds,
    )
    try:
        store.check_available()
    except RedisUnavailableError as exc:
        raise DependencyUnavailableError("Redis short-term memory is required for chat.") from exc
    return store
