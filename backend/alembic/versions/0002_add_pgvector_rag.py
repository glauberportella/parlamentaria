"""Add pgvector extension and document_chunks table for RAG.

Revision ID: 0002_add_pgvector_rag
Revises: 0001_initial
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0002_add_pgvector_rag"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 768  # gemini-embedding-001 default


def upgrade() -> None:
    """Create pgvector extension and document_chunks table."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposicao_id", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("metadata_extra", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["proposicao_id"], ["proposicoes.id"], ondelete="CASCADE"
        ),
    )

    # Create indexes
    op.create_index(
        "ix_document_chunks_proposicao_id",
        "document_chunks",
        ["proposicao_id"],
    )
    op.create_index(
        "ix_document_chunks_chunk_type",
        "document_chunks",
        ["chunk_type"],
    )
    op.create_index(
        "ix_document_chunks_content_hash",
        "document_chunks",
        ["content_hash"],
    )

    # Create HNSW index for fast approximate nearest neighbor search
    # Using cosine distance (<=>) which works best for normalized embeddings
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Drop document_chunks table and pgvector extension."""
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index("ix_document_chunks_content_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_chunk_type", table_name="document_chunks")
    op.drop_index("ix_document_chunks_proposicao_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
