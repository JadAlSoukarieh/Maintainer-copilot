"""add pgvector-backed memory embeddings

Revision ID: 0003_memory_pgvector
Revises: 0002_auth_and_widgets
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_memory_pgvector"
down_revision = "0002_auth_and_widgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding vector(384)")
    else:
        op.add_column("memories", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS embedding")
    else:
        op.drop_column("memories", "embedding")
