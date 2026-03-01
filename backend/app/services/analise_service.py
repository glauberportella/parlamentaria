"""Service for AnaliseIA — AI analysis of legislative propositions."""

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analise_ia import AnaliseIA
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.analise_ia import AnaliseIARepository
from app.repositories.proposicao import ProposicaoRepository
from app.schemas.analise_ia import AnaliseIACreate

logger = get_logger(__name__)


class AnaliseIAService:
    """Orchestrates AI analysis creation and retrieval for propositions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnaliseIARepository(session)
        self.proposicao_repo = ProposicaoRepository(session)

    async def get_latest(self, proposicao_id: int) -> AnaliseIA | None:
        """Get the latest AI analysis for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Latest AnaliseIA or None if never analysed.
        """
        return await self.repo.find_latest_by_proposicao(proposicao_id)

    async def get_latest_or_raise(self, proposicao_id: int) -> AnaliseIA:
        """Get the latest analysis, raising if none exists.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            AnaliseIA instance.

        Raises:
            NotFoundException: If no analysis exists for this proposition.
        """
        analise = await self.repo.find_latest_by_proposicao(proposicao_id)
        if analise is None:
            raise NotFoundException(
                detail=f"Nenhuma análise encontrada para proposição {proposicao_id}"
            )
        return analise

    async def list_versions(self, proposicao_id: int) -> Sequence[AnaliseIA]:
        """List all analysis versions for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Sequence of analyses ordered by version desc.
        """
        return await self.repo.list_by_proposicao(proposicao_id)

    async def create_analysis(self, data: AnaliseIACreate) -> AnaliseIA:
        """Create a new AI analysis for a proposition.

        Automatically increments the version number.

        Args:
            data: Validated analysis data.

        Returns:
            Created AnaliseIA.

        Raises:
            NotFoundException: If the proposition doesn't exist.
        """
        # Verify proposition exists
        await self.proposicao_repo.get_by_id_or_raise(data.proposicao_id)

        # Determine next version
        latest = await self.repo.find_latest_by_proposicao(data.proposicao_id)
        next_version = (latest.versao + 1) if latest else 1

        analise = AnaliseIA(**data.model_dump(), versao=next_version)
        result = await self.repo.create(analise)
        logger.info(
            "analise_ia.created",
            proposicao_id=data.proposicao_id,
            versao=next_version,
            provedor=data.provedor_llm,
        )

        # Update proposição with summary
        proposicao = await self.proposicao_repo.get_by_id(data.proposicao_id)
        if proposicao:
            await self.proposicao_repo.update(proposicao, {
                "resumo_ia": data.resumo_leigo,
            })

        return result
