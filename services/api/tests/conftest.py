from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from maintcopilot_api.domain.auth import UserRole
from maintcopilot_api.infra.auth import JWTManager, PasswordHasher
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.repositories.auth_repository import AuthRepository
from maintcopilot_api.repositories.base import metadata
from maintcopilot_api.repositories.widget_repository import WidgetRepository
from maintcopilot_api.services.auth_service import AuthService
from maintcopilot_api.services.widget_service import WidgetService


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret="test-jwt-secret", require_vault=False, invite_exp_hours=24)


@pytest.fixture
def password_hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def jwt_manager(settings: Settings) -> JWTManager:
    return JWTManager(secret=settings.jwt_secret or "test-jwt-secret", expires_minutes=settings.jwt_exp_minutes)


@pytest.fixture
def auth_repository(session: Session) -> AuthRepository:
    return AuthRepository(session=session)


@pytest.fixture
def audit_repository(session: Session) -> AuditRepository:
    return AuditRepository(session=session)


@pytest.fixture
def widget_repository(session: Session) -> WidgetRepository:
    return WidgetRepository(session=session)


@pytest.fixture
def auth_service(
    session: Session,
    settings: Settings,
    password_hasher: PasswordHasher,
    jwt_manager: JWTManager,
    auth_repository: AuthRepository,
    audit_repository: AuditRepository,
) -> AuthService:
    return AuthService(
        repository=auth_repository,
        audit_repository=audit_repository,
        session=session,
        password_hasher=password_hasher,
        jwt_manager=jwt_manager,
        settings=settings,
    )


@pytest.fixture
def widget_service(
    session: Session,
    widget_repository: WidgetRepository,
    audit_repository: AuditRepository,
) -> WidgetService:
    return WidgetService(repository=widget_repository, audit_repository=audit_repository, session=session)


@pytest.fixture
def seed_user(auth_repository: AuthRepository, password_hasher: PasswordHasher, session: Session):
    def _seed(*, email: str, role: UserRole = UserRole.USER, is_active: bool = True) -> dict:
        user = auth_repository.create_user(
            email=email,
            hashed_password=password_hasher.hash_password("password123"),
            role=role,
            is_active=is_active,
        )
        session.commit()
        return user

    return _seed
