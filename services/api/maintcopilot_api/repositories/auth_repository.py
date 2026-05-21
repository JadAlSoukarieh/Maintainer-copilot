from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete as sa_delete, insert, select, update
from sqlalchemy.orm import Session

from maintcopilot_api.domain.auth import UserRole
from maintcopilot_api.repositories.base import user_invites, users


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_user_by_email(self, email: str) -> dict | None:
        row = self._session.execute(select(users).where(users.c.email == email)).mappings().first()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> dict | None:
        row = self._session.execute(select(users).where(users.c.id == user_id)).mappings().first()
        return dict(row) if row else None

    def create_user(
        self,
        *,
        email: str,
        hashed_password: str,
        role: UserRole,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
    ) -> dict:
        user_id = str(uuid.uuid4())
        self._session.execute(
            insert(users).values(
                id=user_id,
                email=email,
                hashed_password=hashed_password,
                role=role.value,
                is_active=is_active,
                is_superuser=is_superuser,
                is_verified=is_verified,
            )
        )
        return self.get_user_by_id(user_id) or {}

    def update_user(self, user_id: str, **kwargs: object) -> dict | None:
        allowed = {"hashed_password", "is_active", "is_superuser", "is_verified"}
        values = {k: v for k, v in kwargs.items() if k in allowed}
        if values:
            self._session.execute(update(users).where(users.c.id == user_id).values(**values))
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> None:
        self._session.execute(sa_delete(users).where(users.c.id == user_id))

    def create_invite(
        self,
        *,
        email: str,
        role: UserRole,
        token_hash: str,
        invited_by_user_id: str,
        expires_at: datetime,
    ) -> dict:
        invite_id = str(uuid.uuid4())
        self._session.execute(
            insert(user_invites).values(
                id=invite_id,
                email=email,
                role=role.value,
                token_hash=token_hash,
                invited_by_user_id=invited_by_user_id,
                expires_at=expires_at,
            )
        )
        return self.get_invite_by_id(invite_id) or {}

    def get_invite_by_id(self, invite_id: str) -> dict | None:
        row = self._session.execute(select(user_invites).where(user_invites.c.id == invite_id)).mappings().first()
        return dict(row) if row else None

    def get_invite_by_token_hash(self, token_hash: str) -> dict | None:
        row = self._session.execute(select(user_invites).where(user_invites.c.token_hash == token_hash)).mappings().first()
        return dict(row) if row else None

    def mark_invite_accepted(self, invite_id: str, accepted_at: datetime) -> dict | None:
        self._session.execute(
            update(user_invites)
            .where(user_invites.c.id == invite_id)
            .values(accepted_at=accepted_at)
        )
        return self.get_invite_by_id(invite_id)

    def create_user_for_tests(
        self,
        *,
        email: str,
        hashed_password: str,
        role: UserRole,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
    ) -> dict:
        return self.create_user(
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
            is_superuser=is_superuser,
            is_verified=is_verified,
        )
