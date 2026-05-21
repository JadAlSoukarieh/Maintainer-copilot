"""add pgvector ANN index for memory embeddings

Revision ID: 0005_memory_pgvector_ann_index
Revises: 0004_fastapi_users_columns
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op

revision = "0005_memory_pgvector_ann_index"
down_revision = "0004_fastapi_users_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    try:
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_memories_embedding_hnsw
            ON memories
            USING hnsw (embedding vector_cosine_ops)
            """
        )
    except Exception:
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_memories_embedding_ivfflat
            ON memories
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_memories_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_memories_embedding_ivfflat")
