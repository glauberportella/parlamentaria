"""Service for VotoPopular (popular vote) business logic."""

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.voto_popular import VotoPopular, VotoEnum
from app.exceptions import NotFoundException, ValidationException
from app.logging import get_logger
from app.repositories.proposicao import ProposicaoRepository
from app.repositories.voto_popular import VotoPopularRepository

logger = get_logger(__name__)


class VotoPopularService:
    """Orchestrates popular voting on legislative propositions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VotoPopularRepository(session)
        self.proposicao_repo = ProposicaoRepository(session)

    async def registrar_voto(
        self,
        eleitor_id: uuid.UUID,
        proposicao_id: int,
        voto: VotoEnum,
        justificativa: str | None = None,
    ) -> VotoPopular:
        """Register or update a voter's vote on a proposition.

        Idempotent: if the voter already voted on this proposition,
        the existing vote is updated (last vote wins).

        Args:
            eleitor_id: Voter UUID.
            proposicao_id: Proposition ID.
            voto: Vote value (SIM, NAO, ABSTENCAO).
            justificativa: Optional justification text.

        Returns:
            The created or updated VotoPopular.

        Raises:
            NotFoundException: If the proposition doesn't exist.
        """
        # Verify proposition exists
        await self.proposicao_repo.get_by_id_or_raise(proposicao_id)

        existing = await self.repo.find_by_eleitor_proposicao(eleitor_id, proposicao_id)
        if existing:
            update_data = {"voto": voto}
            if justificativa is not None:
                update_data["justificativa"] = justificativa
            result = await self.repo.update(existing, update_data)
            logger.info(
                "voto_popular.updated",
                eleitor_id=str(eleitor_id),
                proposicao_id=proposicao_id,
                voto=voto.value,
            )
            return result

        voto_popular = VotoPopular(
            eleitor_id=eleitor_id,
            proposicao_id=proposicao_id,
            voto=voto,
            justificativa=justificativa,
        )
        result = await self.repo.create(voto_popular)
        logger.info(
            "voto_popular.created",
            eleitor_id=str(eleitor_id),
            proposicao_id=proposicao_id,
            voto=voto.value,
        )
        return result

    async def obter_resultado(self, proposicao_id: int) -> dict:
        """Get the consolidated popular vote result for a proposition.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Dict with SIM, NAO, ABSTENCAO counts, total, and percentages.
        """
        counts = await self.repo.count_by_proposicao(proposicao_id)
        total = counts["total"]

        result = {
            **counts,
            "percentual_sim": round(counts["SIM"] / total * 100, 1) if total else 0.0,
            "percentual_nao": round(counts["NAO"] / total * 100, 1) if total else 0.0,
            "percentual_abstencao": round(counts["ABSTENCAO"] / total * 100, 1) if total else 0.0,
        }
        return result

    async def list_by_eleitor(
        self, eleitor_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> Sequence[VotoPopular]:
        """List all votes by a specific voter.

        Args:
            eleitor_id: Voter UUID.
            offset: Records to skip.
            limit: Maximum records.

        Returns:
            Sequence of votes.
        """
        return await self.repo.list_by_eleitor(eleitor_id, offset, limit)

    async def get_voto(
        self, eleitor_id: uuid.UUID, proposicao_id: int
    ) -> VotoPopular | None:
        """Check if a voter has voted on a proposition.

        Args:
            eleitor_id: Voter UUID.
            proposicao_id: Proposition ID.

        Returns:
            VotoPopular or None.
        """
        return await self.repo.find_by_eleitor_proposicao(eleitor_id, proposicao_id)
