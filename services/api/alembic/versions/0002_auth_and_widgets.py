"""auth foundation and widget admin fields

Revision ID: 0002_auth_and_widgets
Revises: 0001_baseline
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_auth_and_widgets"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def now() -> sa.sql.functions.Function:
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
    )

    op.create_table(
        "user_invites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now()),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_user_invites_role"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.add_column("widgets", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("widgets", sa.Column("created_by_user_id", sa.String(length=36), nullable=True))
    op.add_column("widgets", sa.Column("updated_by_user_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_widgets_created_by_user_id_users",
        "widgets",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_widgets_updated_by_user_id_users",
        "widgets",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_widgets_updated_by_user_id_users", "widgets", type_="foreignkey")
    op.drop_constraint("fk_widgets_created_by_user_id_users", "widgets", type_="foreignkey")
    op.drop_column("widgets", "updated_by_user_id")
    op.drop_column("widgets", "created_by_user_id")
    op.drop_column("widgets", "is_active")
    op.drop_table("user_invites")
    op.drop_table("users")
