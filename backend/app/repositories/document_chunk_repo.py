"""Repository for DocumentChunk — vector storage and similarity search."""

from typing import Any, Sequence

from sqlalchemy import select, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.document_chunk import DocumentChunk
from app.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for vector chunk CRUD and similarity search operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentChunk, session)

    async def find_by_proposicao_and_type_and_hash(
        self,
        proposicao_id: int,
        chunk_type: str,
        content_hash: str,
    ) -> DocumentChunk | None:
        """Find a chunk by proposição, type, and content hash.

        Used to check if identical content has already been embedded.

        Args:
            proposicao_id: Proposição ID.
            chunk_type: Chunk type string.
            content_hash: SHA-256 hash of the content.

        Returns:
            DocumentChunk or None.
        """
        stmt = select(DocumentChunk).where(
            DocumentChunk.proposicao_id == proposicao_id,
            DocumentChunk.chunk_type == chunk_type,
            DocumentChunk.content_hash == content_hash,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_proposicao(
        self, proposicao_id: int
    ) -> Sequence[DocumentChunk]:
        """Get all chunks for a proposição.

        Args:
            proposicao_id: Proposição ID.

        Returns:
            Sequence of DocumentChunk.
        """
        stmt = select(DocumentChunk).where(
            DocumentChunk.proposicao_id == proposicao_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_proposicao_and_type(
        self,
        proposicao_id: int,
        chunk_type: str,
    ) -> int:
        """Delete chunks by proposição and type.

        Used when re-indexing updated content.

        Args:
            proposicao_id: Proposição ID.
            chunk_type: Chunk type to delete.

        Returns:
            Number of rows deleted.
        """
        stmt = delete(DocumentChunk).where(
            DocumentChunk.proposicao_id == proposicao_id,
            DocumentChunk.chunk_type == chunk_type,
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_by_proposicao(self, proposicao_id: int) -> int:
        """Delete all chunks for a proposição.

        Args:
            proposicao_id: Proposição ID.

        Returns:
            Number of rows deleted.
        """
        stmt = delete(DocumentChunk).where(
            DocumentChunk.proposicao_id == proposicao_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def similarity_search(
        self,
        embedding: list[float],
        limit: int = 10,
        threshold: float = 0.3,
        chunk_types: list[str] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform cosine similarity search on embeddings.

        Uses pgvector's cosine distance operator (<=>).
        Distance = 1 - similarity, so lower distance = more similar.

        Args:
            embedding: Query embedding vector.
            limit: Maximum results.
            threshold: Maximum cosine distance (1 - similarity).
                       Default 0.3 means similarity >= 0.7.
            chunk_types: Optional filter by chunk types.

        Returns:
            List of (DocumentChunk, distance) tuples, ordered by distance ASC.
        """
        # Build the distance expression
        distance_expr = DocumentChunk.embedding.cosine_distance(embedding)

        stmt = (
            select(DocumentChunk, distance_expr.label("distance"))
            .where(distance_expr <= threshold)
        )

        if chunk_types:
            stmt = stmt.where(DocumentChunk.chunk_type.in_(chunk_types))

        stmt = stmt.order_by(distance_expr).limit(limit)

        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_stats(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dict with total_chunks, by_type counts, unique_proposicoes.
        """
        # Total chunks
        total_stmt = select(func.count()).select_from(DocumentChunk)
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one()

        # Count by type
        type_stmt = select(
            DocumentChunk.chunk_type,
            func.count().label("count"),
        ).group_by(DocumentChunk.chunk_type)
        type_result = await self.session.execute(type_stmt)
        by_type = {row[0]: row[1] for row in type_result.all()}

        # Unique proposições
        unique_stmt = select(
            func.count(func.distinct(DocumentChunk.proposicao_id))
        )
        unique_result = await self.session.execute(unique_stmt)
        unique_proposicoes = unique_result.scalar_one()

        return {
            "total_chunks": total,
            "by_type": by_type,
            "unique_proposicoes": unique_proposicoes,
        }
