from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_memory_ann_migration_exists_and_uses_pgvector_ann_index() -> None:
    migration = ROOT / "services/api/alembic/versions/0005_memory_pgvector_ann_index.py"
    source = migration.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in source
    assert "ix_memories_embedding_hnsw" in source
    assert "USING hnsw" in source or "USING ivfflat" in source
