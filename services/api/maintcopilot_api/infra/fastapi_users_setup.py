from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import BaseUserDatabase
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

from maintcopilot_api.domain.auth import UserRole
from maintcopilot_api.infra.auth import PasswordHasher
from maintcopilot_api.repositories.auth_repository import AuthRepository


# ----- Internal user model -----

@dataclass
class UserFU:
    """Internal user representation for the fastapi-users protocol."""
    id: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    role: UserRole = field(default=UserRole.USER)


# ----- API schemas -----

class FUUserRead(BaseUser[str]):
    role: UserRole = UserRole.USER


class FUUserCreate(BaseUserCreate):
    role: UserRole = UserRole.USER


class FUUserUpdate(BaseUserUpdate):
    pass


# ----- Database adapter (sync → async bridge) -----

class SyncUserDatabase(BaseUserDatabase[UserFU, str]):
    def __init__(self, repository: AuthRepository) -> None:
        self._repo = repository

    async def get(self, user_id: str) -> Optional[UserFU]:
        record = await asyncio.to_thread(self._repo.get_user_by_id, user_id)
        return _record_to_user(record) if record else None

    async def get_by_email(self, email: str) -> Optional[UserFU]:
        record = await asyncio.to_thread(self._repo.get_user_by_email, email)
        return _record_to_user(record) if record else None

    async def create(self, create_dict: dict[str, Any]) -> UserFU:
        def _create() -> dict:
            record = self._repo.create_user(
                email=create_dict["email"],
                hashed_password=create_dict["hashed_password"],
                role=UserRole(create_dict.get("role", "user")),
                is_active=bool(create_dict.get("is_active", True)),
                is_superuser=bool(create_dict.get("is_superuser", False)),
                is_verified=bool(create_dict.get("is_verified", False)),
            )
            self._repo._session.commit()
            return record

        record = await asyncio.to_thread(_create)
        return _record_to_user(record)

    async def update(self, user: UserFU, update_dict: dict[str, Any]) -> UserFU:
        def _update() -> dict | None:
            record = self._repo.update_user(user.id, **update_dict)
            self._repo._session.commit()
            return record

        record = await asyncio.to_thread(_update)
        return _record_to_user(record or {})

    async def delete(self, user: UserFU) -> None:
        def _delete() -> None:
            self._repo.delete_user(user.id)
            self._repo._session.commit()

        await asyncio.to_thread(_delete)


# ----- Password helper (wraps our scrypt PasswordHasher) -----

class MaintcopilotPasswordHelper:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def verify_and_update(self, plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
        return self._hasher.verify_password(plain_password, hashed_password), None

    def hash(self, password: str) -> str:
        return self._hasher.hash_password(password)

    def generate(self) -> str:
        return secrets.token_urlsafe(32)


# ----- User manager -----

class MaintcopilotUserManager(BaseUserManager[UserFU, str]):
    def __init__(
        self,
        user_db: SyncUserDatabase,
        password_helper: MaintcopilotPasswordHelper,
        *,
        jwt_secret: str,
    ) -> None:
        super().__init__(user_db, password_helper)
        self.reset_password_token_secret = jwt_secret
        self.verification_token_secret = jwt_secret

    async def on_after_register(self, user: UserFU, request: Optional[Any] = None) -> None:
        pass


# ----- FastAPI dependency functions -----

async def get_user_db(request: Request):
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield SyncUserDatabase(AuthRepository(session=session))
    finally:
        session.close()


async def get_user_manager(
    request: Request,
    user_db: SyncUserDatabase = Depends(get_user_db),
):
    settings = request.app.state.settings
    jwt_secret = settings.jwt_secret or "dev-only-jwt-secret"
    yield MaintcopilotUserManager(user_db, MaintcopilotPasswordHelper(), jwt_secret=jwt_secret)


async def get_jwt_strategy(request: Request) -> JWTStrategy:
    settings = request.app.state.settings
    return JWTStrategy(
        secret=settings.jwt_secret or "dev-only-jwt-secret",
        lifetime_seconds=(settings.jwt_exp_minutes or 60) * 60,
    )


# ----- Auth backend & FastAPIUsers instance -----

bearer_transport = BearerTransport(tokenUrl="/auth/v2/login")

auth_backend = AuthenticationBackend(
    name="jwt-v2",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserFU, str](
    get_user_manager,
    [auth_backend],
)


# ----- Helper -----

def _record_to_user(record: dict) -> UserFU:
    return UserFU(
        id=str(record["id"]),
        email=str(record["email"]),
        hashed_password=str(record.get("hashed_password", "")),
        is_active=bool(record.get("is_active", True)),
        is_superuser=bool(record.get("is_superuser", False)),
        is_verified=bool(record.get("is_verified", False)),
        role=UserRole(record.get("role", "user")),
    )
