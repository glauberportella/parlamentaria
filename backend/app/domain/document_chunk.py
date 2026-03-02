"""DocumentChunk domain model — vectorized text chunks for RAG search.

Each chunk holds a piece of legislative text (ementa, resumo IA, análise)
along with its embedding vector for semantic similarity search via pgvector.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.config import settings
from app.db.base import Base


class ChunkType(str, PyEnum):
    """Type of content stored in the chunk."""

    EMENTA = "ementa"
    RESUMO_IA = "resumo_ia"
    ANALISE_RESUMO_LEIGO = "analise_resumo_leigo"
    ANALISE_IMPACTO = "analise_impacto"
    ANALISE_ARGUMENTOS = "analise_argumentos"
    TRAMITACAO = "tramitacao"


class DocumentChunk(Base):
    """A vectorized text chunk for semantic search (RAG).

    Each proposição can have multiple chunks (ementa, resumo, análise, etc.),
    enabling fine-grained semantic retrieval.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposicao_id: Mapped[int] = mapped_column(
        ForeignKey("proposicoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_type: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Type of content: ementa, resumo_ia, analise, etc."
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Original text content of the chunk"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, doc="SHA-256 hash to avoid re-embedding identical content"
    )
    embedding: Mapped[list] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=False, doc="Vector embedding"
    )
    metadata_extra: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Extra metadata as JSON string (tipo, numero, ano, etc.)"
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Model used to generate embedding"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk prop={self.proposicao_id} type={self.chunk_type}>"
