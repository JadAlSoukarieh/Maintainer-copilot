from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials
import pytest

from maintcopilot_api.api.deps import get_current_user, require_admin
from maintcopilot_api.api.routes.auth import accept_invite, create_invite, login, me, register
from maintcopilot_api.domain.auth import (
    AcceptInviteRequest,
    CreateInviteRequest,
    LoginRequest,
    RegisterRequest,
    UserRead,
    UserRole,
)
from maintcopilot_api.domain.errors import ForbiddenError


def test_register_user(auth_service) -> None:
    user = register(RegisterRequest(email="user@example.com", password="password123"), auth_service)
    assert user.email == "user@example.com"
    assert user.role == UserRole.USER
    stored = auth_service._repository.get_user_by_email("user@example.com")
    assert stored is not None
    assert stored["hashed_password"] != "password123"


def test_login_returns_jwt(auth_service) -> None:
    register(RegisterRequest(email="user@example.com", password="password123"), auth_service)
    token = login(LoginRequest(email="user@example.com", password="password123"), auth_service)
    assert token.token_type == "bearer"
    assert token.access_token.count(".") == 2
    assert token.expires_in > 0


def test_auth_me_works_with_jwt(auth_service) -> None:
    register(RegisterRequest(email="user@example.com", password="password123"), auth_service)
    token = login(LoginRequest(email="user@example.com", password="password123"), auth_service)
    current_user = get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token.access_token),
        auth_service,
    )
    response = me(current_user)
    assert response.email == "user@example.com"


def test_admin_only_route_rejects_normal_user(auth_service) -> None:
    user = register(RegisterRequest(email="user@example.com", password="password123"), auth_service)
    with pytest.raises(ForbiddenError):
        require_admin(user)


def test_admin_only_route_accepts_admin(auth_service, seed_user) -> None:
    admin_record = seed_user(email="admin@example.com", role=UserRole.ADMIN)
    admin_user = UserRead(**admin_record)
    result = require_admin(admin_user)
    assert result.role == UserRole.ADMIN


def test_inactive_user_cannot_authenticate(auth_service, seed_user) -> None:
    seed_user(email="inactive@example.com", role=UserRole.USER, is_active=False)
    with pytest.raises(ForbiddenError):
        login(LoginRequest(email="inactive@example.com", password="password123"), auth_service)


def test_admin_can_create_and_accept_invite(auth_service, seed_user, audit_repository) -> None:
    admin_record = seed_user(email="admin@example.com", role=UserRole.ADMIN)
    admin_user = UserRead(**admin_record)
    invite = create_invite(
        CreateInviteRequest(email="invited@example.com", role=UserRole.USER, expires_in_hours=12),
        admin_user,
        auth_service,
    )
    invited_user = accept_invite(
        AcceptInviteRequest(token=invite.invite_token, password="password123"),
        auth_service,
    )
    event_types = [event["event_type"] for event in audit_repository.list_events()]
    assert invited_user.email == "invited@example.com"
    assert "invite_created" in event_types
    assert "invite_accepted" in event_types
