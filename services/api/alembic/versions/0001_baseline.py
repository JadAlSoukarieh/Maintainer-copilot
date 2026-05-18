"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def now() -> sa.sql.functions.Function:
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "retrieved_chunk_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("chunks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "widgets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("public_widget_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("allowed_origins", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("theme", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("greeting", sa.Text(), nullable=False, server_default="Hello from Maintainer's Copilot."),
        sa.Column("enabled_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
    )


def downgrade() -> None:
    op.drop_table("widgets")
    op.drop_table("retrieved_chunk_snapshots")
    op.drop_table("memories")
    op.drop_table("conversations")
    op.drop_table("audit_logs")

