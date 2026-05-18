from __future__ import annotations

from datetime import datetime, timedelta, timezone

from maintcopilot_api.domain.auth import (
    AcceptInviteRequest,
    CreateInviteRequest,
    InviteCreatedResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
    UserRole,
)
from maintcopilot_api.domain.errors import AuthenticationError, ConflictError, ForbiddenError, NotFoundError
from maintcopilot_api.infra.auth import JWTManager, PasswordHasher, TokenError
from maintcopilot_api.infra.config import Settings
from maintcopilot_api.repositories.audit_repository import AuditRepository
from maintcopilot_api.repositories.auth_repository import AuthRepository


class AuthService:
    def __init__(
        self,
        *,
        repository: AuthRepository,
        audit_repository: AuditRepository,
        session,
        password_hasher: PasswordHasher,
        jwt_manager: JWTManager,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._session = session
        self._password_hasher = password_hasher
        self._jwt_manager = jwt_manager
        self._settings = settings

    def register(self, payload: RegisterRequest) -> UserRead:
        if self._repository.get_user_by_email(payload.email):
            raise ConflictError("A user with this email already exists.")
        hashed_password = self._password_hasher.hash_password(payload.password)
        record = self._repository.create_user(
            email=payload.email,
            hashed_password=hashed_password,
            role=UserRole.USER,
            is_active=True,
        )
        self._session.commit()
        return UserRead(**record)

    def login(self, payload: LoginRequest) -> TokenResponse:
        record = self._repository.get_user_by_email(payload.email)
        if record is None or not self._password_hasher.verify_password(payload.password, record["hashed_password"]):
            raise AuthenticationError("Invalid email or password.")
        if not record["is_active"]:
            raise ForbiddenError("Inactive users cannot authenticate.")
        token, expires_in = self._jwt_manager.create_token(
            subject=record["id"],
            email=record["email"],
            role=record["role"],
            is_active=record["is_active"],
        )
        return TokenResponse(access_token=token, expires_in=expires_in)

    def get_current_user(self, token: str) -> UserRead:
        payload = self._jwt_manager.decode_token(token)
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise TokenError("Token subject is missing.")
        record = self._repository.get_user_by_id(subject)
        if record is None:
            raise AuthenticationError("Authenticated user was not found.")
        if not record["is_active"]:
            raise ForbiddenError("Inactive users cannot authenticate.")
        return UserRead(**record)

    def create_invite(self, payload: CreateInviteRequest, current_user: UserRead) -> InviteCreatedResponse:
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenError("Admin access is required.")
        if self._repository.get_user_by_email(payload.email):
            raise ConflictError("A user with this email already exists.")

        invite_token = self._jwt_manager.generate_invite_token()
        token_hash = self._jwt_manager.hash_invite_token(invite_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=payload.expires_in_hours or self._settings.invite_exp_hours
        )
        invite = self._repository.create_invite(
            email=payload.email,
            role=payload.role,
            token_hash=token_hash,
            invited_by_user_id=current_user.id,
            expires_at=expires_at,
        )
        self._audit_repository.create_event(
            event_type="invite_created",
            actor_id=current_user.id,
            payload={"email": payload.email, "role": payload.role.value, "invite_id": invite["id"]},
        )
        self._session.commit()
        return InviteCreatedResponse(
            id=invite["id"],
            email=invite["email"],
            role=UserRole(invite["role"]),
            expires_at=invite["expires_at"],
            invite_token=invite_token,
        )

    def accept_invite(self, payload: AcceptInviteRequest) -> UserRead:
        token_hash = self._jwt_manager.hash_invite_token(payload.token)
        invite = self._repository.get_invite_by_token_hash(token_hash)
        if invite is None:
            raise NotFoundError("Invite token was not found.")
        if invite["accepted_at"] is not None:
            raise ConflictError("Invite has already been accepted.")
        if _coerce_utc(invite["expires_at"]) < datetime.now(timezone.utc):
            raise ForbiddenError("Invite has expired.")
        if self._repository.get_user_by_email(invite["email"]):
            raise ConflictError("A user with this email already exists.")

        hashed_password = self._password_hasher.hash_password(payload.password)
        user = self._repository.create_user(
            email=invite["email"],
            hashed_password=hashed_password,
            role=UserRole(invite["role"]),
            is_active=True,
        )
        self._repository.mark_invite_accepted(invite["id"], datetime.now(timezone.utc))
        self._audit_repository.create_event(
            event_type="invite_accepted",
            actor_id=user["id"],
            payload={"invite_id": invite["id"], "email": invite["email"], "role": invite["role"]},
        )
        self._session.commit()
        return UserRead(**user)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
