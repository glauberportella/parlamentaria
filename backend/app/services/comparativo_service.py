"""Service for ComparativoVotacao — comparing popular and parliamentary votes."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.proposicao import ProposicaoRepository
from app.repositories.votacao import VotacaoRepository
from app.repositories.voto_popular import VotoPopularRepository

logger = get_logger(__name__)


def calcular_alinhamento(voto_popular: dict, resultado_camara: str) -> float:
    """Calculate the alignment index between popular vote and parliamentary result.

    Args:
        voto_popular: Dict with "SIM" and "NAO" counts.
        resultado_camara: "APROVADO" or "REJEITADO".

    Returns:
        Float 0.0 (total divergence) to 1.0 (total alignment).
    """
    sim = voto_popular.get("SIM", 0)
    nao = voto_popular.get("NAO", 0)
    total = sim + nao
    if total == 0:
        return 0.5

    maioria_popular = "SIM" if sim > nao else "NAO"
    alinhado = maioria_popular == ("SIM" if resultado_camara == "APROVADO" else "NAO")

    forca = max(sim, nao) / total
    return round(forca if alinhado else 1.0 - forca, 4)


class ComparativoService:
    """Orchestrates comparison between popular votes and parliamentary results."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.proposicao_repo = ProposicaoRepository(session)
        self.votacao_repo = VotacaoRepository(session)
        self.voto_popular_repo = VotoPopularRepository(session)

    async def gerar_comparativo(
        self,
        proposicao_id: int,
        votacao_camara_id: int,
        resultado_camara: str,
        votos_camara_sim: int,
        votos_camara_nao: int,
    ) -> ComparativoVotacao:
        """Generate a comparative analysis between popular and parliamentary votes.

        Args:
            proposicao_id: Proposition ID.
            votacao_camara_id: Parliamentary vote session ID.
            resultado_camara: "APROVADO" or "REJEITADO".
            votos_camara_sim: Total parliamentary YES votes.
            votos_camara_nao: Total parliamentary NO votes.

        Returns:
            Created ComparativoVotacao.

        Raises:
            NotFoundException: If proposition doesn't exist.
        """
        await self.proposicao_repo.get_by_id_or_raise(proposicao_id)

        # Get popular vote counts
        counts = await self.voto_popular_repo.count_by_proposicao(proposicao_id)

        alinhamento = calcular_alinhamento(counts, resultado_camara)

        comparativo = ComparativoVotacao(
            proposicao_id=proposicao_id,
            votacao_camara_id=votacao_camara_id,
            voto_popular_sim=counts["SIM"],
            voto_popular_nao=counts["NAO"],
            voto_popular_abstencao=counts["ABSTENCAO"],
            resultado_camara=resultado_camara,
            votos_camara_sim=votos_camara_sim,
            votos_camara_nao=votos_camara_nao,
            alinhamento=alinhamento,
        )

        self.session.add(comparativo)
        await self.session.flush()
        await self.session.refresh(comparativo)

        logger.info(
            "comparativo.created",
            proposicao_id=proposicao_id,
            votacao_camara_id=votacao_camara_id,
            alinhamento=alinhamento,
        )
        return comparativo

    async def get_by_proposicao(self, proposicao_id: int) -> ComparativoVotacao | None:
        """Get the comparative for a proposition, if any.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            ComparativoVotacao or None.
        """
        from sqlalchemy import select

        stmt = select(ComparativoVotacao).where(
            ComparativoVotacao.proposicao_id == proposicao_id
        ).order_by(ComparativoVotacao.data_geracao.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
