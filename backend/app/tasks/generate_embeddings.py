"""Celery task: generate embeddings for propositions (RAG indexing).

This task indexes propositions into the document_chunks table with
pgvector embeddings for semantic search. Designed to run:
1. After sync_proposicoes_task completes (chained)
2. On-demand via admin endpoint
3. Periodically via Celery beat for full re-index
"""

import asyncio

from app.tasks.celery_app import celery_app
from app.tasks.helpers import get_async_session
from app.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.generate_embeddings.generate_embeddings_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_embeddings_task(
    self,
    proposicao_id: int | None = None,
    batch_size: int = 50,
    offset: int = 0,
) -> dict:
    """Generate embeddings for propositions and store in pgvector.

    Can index a single proposição (by ID) or batch-process multiple.

    Args:
        proposicao_id: If provided, index only this proposição.
        batch_size: Number of proposições to process in one batch.
        offset: Pagination offset for batch processing.

    Returns:
        Dict with indexing statistics.
    """
    logger.info(
        "task.generate_embeddings.start",
        proposicao_id=proposicao_id,
        batch_size=batch_size,
        offset=offset,
    )

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.services.rag_service import RAGService

            rag_service = RAGService(session)

            if proposicao_id is not None:
                # Index single proposição
                from app.repositories.proposicao import ProposicaoRepository

                repo = ProposicaoRepository(session)
                proposicao = await repo.get_by_id(proposicao_id)
                if proposicao is None:
                    return {
                        "status": "error",
                        "error": f"Proposição {proposicao_id} não encontrada.",
                    }

                stats = await rag_service.index_proposicao(proposicao)
                await session.commit()
                return {"status": "success", "proposicao_id": proposicao_id, **stats}

            else:
                # Batch index
                stats = await rag_service.reindex_all_proposicoes(
                    limit=batch_size,
                    offset=offset,
                )
                await session.commit()
                return {"status": "success", **stats}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.generate_embeddings.complete", **result)
    return result


@celery_app.task(
    name="app.tasks.generate_embeddings.reindex_all_embeddings_task",
    bind=True,
    max_retries=1,
)
def reindex_all_embeddings_task(self, batch_size: int = 100) -> dict:
    """Full re-index of all propositions — for model changes or initial setup.

    Processes all propositions in batches, dispatching sub-tasks.

    Args:
        batch_size: Propositions per batch.

    Returns:
        Dict with total stats.
    """
    logger.info("task.reindex_all.start", batch_size=batch_size)

    async def _run() -> dict:
        async with get_async_session() as session:
            from app.repositories.proposicao import ProposicaoRepository

            repo = ProposicaoRepository(session)
            total = await repo.count()

            if total == 0:
                return {"status": "success", "message": "No propositions to index.", "total": 0}

            all_stats = {"created": 0, "skipped": 0, "errors": 0, "proposicoes_processed": 0}

            from app.services.rag_service import RAGService

            rag_service = RAGService(session)

            for offset in range(0, total, batch_size):
                batch_stats = await rag_service.reindex_all_proposicoes(
                    limit=batch_size,
                    offset=offset,
                )
                all_stats["created"] += batch_stats["created"]
                all_stats["skipped"] += batch_stats["skipped"]
                all_stats["errors"] += batch_stats["errors"]
                all_stats["proposicoes_processed"] += batch_stats["proposicoes_processed"]
                await session.commit()

            return {"status": "success", **all_stats}

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        result = asyncio.run(_run())

    logger.info("task.reindex_all.complete", **result)
    return result
