from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, Text, func

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

