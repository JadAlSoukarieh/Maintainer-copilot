from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, MetaData, String, Table, Text, func

metadata = MetaData()

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("event_type", String(100), nullable=False),
    Column("actor_id", String(255), nullable=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("hashed_password", Text, nullable=False),
    Column("role", String(20), nullable=False),
    Column("is_active", Boolean, nullable=False, default=True, server_default="1"),
    Column("is_superuser", Boolean, nullable=False, default=False, server_default="0"),
    Column("is_verified", Boolean, nullable=False, default=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

user_invites = Table(
    "user_invites",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), nullable=False),
    Column("role", String(20), nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("invited_by_user_id", String(36), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("accepted_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(255), nullable=True),
    Column("title", String(255), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

memories = Table(
    "memories",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("conversation_id", String(36), nullable=True),
    Column("user_id", String(255), nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata", JSON, nullable=False),
    Column("embedding", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

widgets = Table(
    "widgets",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("public_widget_id", String(100), nullable=False, unique=True),
    Column("allowed_origins", JSON, nullable=False),
    Column("theme", JSON, nullable=False),
    Column("greeting", Text, nullable=False),
    Column("enabled_tools", JSON, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True, server_default="1"),
    Column("created_by_user_id", String(36), nullable=True),
    Column("updated_by_user_id", String(36), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

retrieved_chunk_snapshots = Table(
    "retrieved_chunk_snapshots",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("conversation_id", String(36), nullable=True),
    Column("query_text", Text, nullable=False),
    Column("chunks", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
