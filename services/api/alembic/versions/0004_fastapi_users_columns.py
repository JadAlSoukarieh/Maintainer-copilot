"""add is_superuser and is_verified columns for fastapi-users compatibility

Revision ID: 0004_fastapi_users_columns
Revises: 0003_memory_pgvector
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_fastapi_users_columns"
down_revision = "0003_memory_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "is_verified")
    op.drop_column("users", "is_superuser")
