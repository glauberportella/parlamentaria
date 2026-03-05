"""Alter document_chunks embedding column from 768 to 3072 dimensions.

gemini-embedding-001 produces 3072-dimensional vectors, not 768 like
the deprecated text-embedding-004.

Revision ID: 0006
Revises: 0005
"""

from alembic import op

# revision identifiers
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

OLD_DIMS = 768
NEW_DIMS = 3072


def upgrade() -> None:
    """Widen the embedding vector column from 768 to 3072 dimensions.

    This requires dropping old data since dimensional mismatch would
    cause errors. The reindex task will repopulate embeddings.
    """
    # Delete existing embeddings — they are 768-dim and incompatible
    op.execute("DELETE FROM document_chunks")

    # Drop old HNSW index (dimension-specific)
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")

    # Alter column type
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ALTER COLUMN embedding TYPE vector({NEW_DIMS}) "
        f"USING embedding::vector({NEW_DIMS})"
    )

    # Recreate HNSW index with new dimensions
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """Revert to 768 dimensions (loses all 3072-dim data)."""
    op.execute("DELETE FROM document_chunks")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ALTER COLUMN embedding TYPE vector({OLD_DIMS}) "
        f"USING embedding::vector({OLD_DIMS})"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
