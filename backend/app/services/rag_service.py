"""RAG (Retrieval-Augmented Generation) service for legislative data.

Orchestrates embedding generation, chunk storage/retrieval, and semantic
search over synced propositions, analyses, and other legislative texts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.document_chunk import ChunkType, DocumentChunk
from app.domain.proposicao import Proposicao
from app.logging import get_logger
from app.repositories.document_chunk_repo import DocumentChunkRepository
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class RAGService:
    """Orchestrates RAG operations: indexing, searching, and chunk management.

    This service is responsible for:
    1. Extracting text chunks from propositions and analyses
    2. Generating embeddings and storing them
    3. Performing semantic similarity search
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.repo = DocumentChunkRepository(session)
        self.embedding_service = embedding_service or EmbeddingService()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def index_proposicao(self, proposicao: Proposicao) -> dict[str, int]:
        """Index all text content from a proposição into vector chunks.

        Extracts ementa, resumo_ia, and analysis texts. Skips chunks
        whose content hash already exists (idempotent).

        Args:
            proposicao: The proposicao domain object to index.

        Returns:
            Dict with counts: created, skipped, errors.
        """
        stats = {"created": 0, "skipped": 0, "errors": 0}

        # Build metadata for all chunks of this proposição
        metadata = json.dumps({
            "tipo": proposicao.tipo,
            "numero": proposicao.numero,
            "ano": proposicao.ano,
            "situacao": proposicao.situacao or "",
            "temas": proposicao.temas or [],
        }, ensure_ascii=False)

        # Collect chunks to index
        chunks_to_process: list[tuple[str, str]] = []  # (chunk_type, content)

        # 1. Ementa (always present)
        if proposicao.ementa:
            ementa_text = (
                f"{proposicao.tipo} {proposicao.numero}/{proposicao.ano}: "
                f"{proposicao.ementa}"
            )
            chunks_to_process.append((ChunkType.EMENTA, ementa_text))

        # 2. Resumo IA
        if proposicao.resumo_ia:
            resumo_text = (
                f"Resumo do {proposicao.tipo} {proposicao.numero}/{proposicao.ano}: "
                f"{proposicao.resumo_ia}"
            )
            chunks_to_process.append((ChunkType.RESUMO_IA, resumo_text))

        # 3. Análises IA (if loaded)
        if hasattr(proposicao, "analises") and proposicao.analises:
            latest_analise = max(proposicao.analises, key=lambda a: a.versao)

            if latest_analise.resumo_leigo:
                chunks_to_process.append((
                    ChunkType.ANALISE_RESUMO_LEIGO,
                    f"Análise em linguagem simples do {proposicao.tipo} "
                    f"{proposicao.numero}/{proposicao.ano}: {latest_analise.resumo_leigo}",
                ))

            if latest_analise.impacto_esperado:
                chunks_to_process.append((
                    ChunkType.ANALISE_IMPACTO,
                    f"Impacto esperado do {proposicao.tipo} "
                    f"{proposicao.numero}/{proposicao.ano}: {latest_analise.impacto_esperado}",
                ))

            # Combine arguments for a single chunk
            args_parts = []
            if latest_analise.argumentos_favor:
                args_parts.append(
                    "Argumentos a favor: " + "; ".join(latest_analise.argumentos_favor)
                )
            if latest_analise.argumentos_contra:
                args_parts.append(
                    "Argumentos contra: " + "; ".join(latest_analise.argumentos_contra)
                )
            if args_parts:
                chunks_to_process.append((
                    ChunkType.ANALISE_ARGUMENTOS,
                    f"{proposicao.tipo} {proposicao.numero}/{proposicao.ano} — "
                    + " | ".join(args_parts),
                ))

        # Process all chunks
        for chunk_type, content in chunks_to_process:
            try:
                async with self.session.begin_nested():
                    result = await self._upsert_chunk(
                        proposicao_id=proposicao.id,
                        chunk_type=chunk_type,
                        content=content,
                        metadata=metadata,
                    )
                if result == "created":
                    stats["created"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(
                    "rag.index_chunk_error",
                    proposicao_id=proposicao.id,
                    chunk_type=chunk_type,
                    error=str(e),
                )
                stats["errors"] += 1

        logger.info(
            "rag.index_proposicao.complete",
            proposicao_id=proposicao.id,
            **stats,
        )
        return stats

    async def _upsert_chunk(
        self,
        proposicao_id: int,
        chunk_type: str,
        content: str,
        metadata: str,
    ) -> str:
        """Create or skip a chunk based on content hash.

        Args:
            proposicao_id: ID of the parent proposição.
            chunk_type: Type of chunk (ementa, resumo, etc.).
            content: Text content to embed.
            metadata: JSON metadata string.

        Returns:
            'created' if new chunk was inserted, 'skipped' if identical exists.
        """
        content_hash = EmbeddingService.content_hash(content)

        # Check if chunk with same hash already exists
        existing = await self.repo.find_by_proposicao_and_type_and_hash(
            proposicao_id=proposicao_id,
            chunk_type=chunk_type,
            content_hash=content_hash,
        )
        if existing:
            return "skipped"

        # Delete old chunks of same type for this proposição (re-index)
        await self.repo.delete_by_proposicao_and_type(
            proposicao_id=proposicao_id,
            chunk_type=chunk_type,
        )

        # Generate embedding
        embedding = await self.embedding_service.embed_text(content)

        # Create chunk
        chunk = DocumentChunk(
            id=uuid.uuid4(),
            proposicao_id=proposicao_id,
            chunk_type=chunk_type,
            content=content,
            content_hash=content_hash,
            embedding=embedding,
            metadata_extra=metadata,
            embedding_model=settings.embedding_model,
        )
        await self.repo.create(chunk)
        return "created"

    async def reindex_all_proposicoes(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, int]:
        """Re-index all proposições in the database.

        Useful for initial population or after changing embedding model.

        Args:
            limit: Max proposições to process per batch.
            offset: Offset for pagination.

        Returns:
            Aggregate stats dict.
        """
        from app.repositories.proposicao import ProposicaoRepository

        prop_repo = ProposicaoRepository(self.session)
        proposicoes = await prop_repo.list_all(offset=offset, limit=limit)

        total_stats = {"created": 0, "skipped": 0, "errors": 0, "proposicoes_processed": 0}

        for prop in proposicoes:
            stats = await self.index_proposicao(prop)
            total_stats["created"] += stats["created"]
            total_stats["skipped"] += stats["skipped"]
            total_stats["errors"] += stats["errors"]
            total_stats["proposicoes_processed"] += 1

        logger.info("rag.reindex_all.complete", **total_stats)
        return total_stats

    # ------------------------------------------------------------------
    # Semantic Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int | None = None,
        threshold: float | None = None,
        chunk_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic similarity search over indexed chunks.

        Args:
            query: Natural language query from the voter.
            limit: Maximum results to return.
            threshold: Minimum similarity score (0-1). Higher = more similar.
            chunk_types: Filter by chunk types (e.g., ['ementa', 'resumo_ia']).

        Returns:
            List of dicts with chunk content, metadata, and similarity score.
        """
        limit = limit or settings.rag_max_results
        threshold = threshold or settings.rag_similarity_threshold

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)

        # Search via repository
        results = await self.repo.similarity_search(
            embedding=query_embedding,
            limit=limit,
            threshold=threshold,
            chunk_types=chunk_types,
        )

        # Format results
        formatted = []
        for chunk, distance in results:
            similarity = 1.0 - distance  # cosine distance → similarity

            metadata = {}
            if chunk.metadata_extra:
                try:
                    metadata = json.loads(chunk.metadata_extra)
                except json.JSONDecodeError:
                    pass

            formatted.append({
                "proposicao_id": chunk.proposicao_id,
                "chunk_type": chunk.chunk_type,
                "content": chunk.content,
                "similarity": round(similarity, 4),
                "metadata": metadata,
                "embedding_model": chunk.embedding_model,
            })

        logger.info(
            "rag.search.complete",
            query_length=len(query),
            results_count=len(formatted),
            threshold=threshold,
        )
        return formatted

    async def search_proposicoes(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search proposições by semantic similarity — deduplicated by proposição.

        Groups results by proposicao_id and returns the best match per proposição.

        Args:
            query: Natural language query.
            limit: Max proposições to return.

        Returns:
            List of dicts with proposição info and best matching content.
        """
        # Fetch more results than needed to allow deduplication
        raw_results = await self.search(
            query=query,
            limit=limit * 3,
        )

        # Deduplicate: keep best match per proposição
        seen: dict[int, dict] = {}
        for result in raw_results:
            prop_id = result["proposicao_id"]
            if prop_id not in seen or result["similarity"] > seen[prop_id]["similarity"]:
                seen[prop_id] = result

        # Sort by similarity and limit
        deduplicated = sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)
        return deduplicated[:limit]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the vector index.

        Returns:
            Dict with total chunks, chunks by type, unique proposições, etc.
        """
        return await self.repo.get_stats()

    async def delete_proposicao_chunks(self, proposicao_id: int) -> int:
        """Delete all chunks for a proposição.

        Args:
            proposicao_id: ID of the proposição.

        Returns:
            Number of chunks deleted.
        """
        return await self.repo.delete_by_proposicao(proposicao_id)
