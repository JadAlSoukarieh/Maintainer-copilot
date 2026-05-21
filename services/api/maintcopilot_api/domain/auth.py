from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("A valid email address is required.")
    return normalized


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    _validate_email = field_validator("email")(_normalize_email)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    _validate_email = field_validator("email")(_normalize_email)


class UserRead(BaseModel):
    id: str
    email: str
    role: UserRole
    is_active: bool
    is_superuser: bool = False
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CreateInviteRequest(BaseModel):
    email: str
    role: UserRole = UserRole.USER
    expires_in_hours: int | None = Field(default=None, ge=1, le=720)

    _validate_email = field_validator("email")(_normalize_email)


class InviteCreatedResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    expires_at: datetime
    invite_token: str


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=16, max_length=255)
    password: str = Field(min_length=8, max_length=128)
