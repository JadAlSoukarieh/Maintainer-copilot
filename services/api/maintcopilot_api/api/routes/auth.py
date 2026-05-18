from __future__ import annotations

from fastapi import APIRouter, Depends

from maintcopilot_api.api.deps import get_auth_service, get_current_user, require_admin
from maintcopilot_api.domain.auth import (
    AcceptInviteRequest,
    CreateInviteRequest,
    InviteCreatedResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from maintcopilot_api.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserRead:
    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    return service.login(payload)


@router.get("/me", response_model=UserRead)
def me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    return current_user


@router.post("/invites", response_model=InviteCreatedResponse)
def create_invite(
    payload: CreateInviteRequest,
    current_user: UserRead = Depends(require_admin),
    service: AuthService = Depends(get_auth_service),
) -> InviteCreatedResponse:
    return service.create_invite(payload, current_user)


@router.post("/invites/accept", response_model=UserRead)
def accept_invite(payload: AcceptInviteRequest, service: AuthService = Depends(get_auth_service)) -> UserRead:
    return service.accept_invite(payload)
