"""Service for ComparativoVotacao — comparing popular and parliamentary votes."""

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.exceptions import NotFoundException
from app.logging import get_logger
from app.repositories.comparativo import ComparativoRepository
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
        self.comparativo_repo = ComparativoRepository(session)
        self.proposicao_repo = ProposicaoRepository(session)
        self.votacao_repo = VotacaoRepository(session)
        self.voto_popular_repo = VotoPopularRepository(session)

    async def gerar_comparativo(
        self,
        proposicao_id: int,
        votacao_camara_id: str,
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

        # Get OFICIAL popular vote counts only (eligible Brazilian citizens)
        counts = await self.voto_popular_repo.count_oficiais_by_proposicao(proposicao_id)

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
        return await self.comparativo_repo.get_by_proposicao(proposicao_id)

    async def list_comparativos(
        self, offset: int = 0, limit: int = 50
    ) -> Sequence[ComparativoVotacao]:
        """List all comparatives with pagination.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            Sequence of ComparativoVotacao.
        """
        return await self.comparativo_repo.list_all(offset=offset, limit=limit)

    async def list_recent(self, limit: int = 20) -> Sequence[ComparativoVotacao]:
        """List the most recent comparatives.

        Args:
            limit: Maximum number to return.

        Returns:
            Sequence of recent ComparativoVotacao.
        """
        return await self.comparativo_repo.list_recent(limit=limit)

    async def exists_for_votacao(self, votacao_camara_id: str) -> bool:
        """Check if a comparative already exists for a parliamentary vote.

        Args:
            votacao_camara_id: Parliamentary vote session ID.

        Returns:
            True if a comparative exists.
        """
        return await self.comparativo_repo.exists_for_votacao(votacao_camara_id)

    async def get_comparativo_with_proposicao(
        self, proposicao_id: int
    ) -> dict | None:
        """Get comparative with enriched proposicao details.

        Args:
            proposicao_id: Proposition ID.

        Returns:
            Dict with comparative and proposicao info, or None.
        """
        comparativo = await self.comparativo_repo.get_by_proposicao(proposicao_id)
        if comparativo is None:
            return None

        proposicao = await self.proposicao_repo.get_by_id(proposicao_id)
        alinhamento_pct = round(comparativo.alinhamento * 100, 1)

        total_popular = (
            comparativo.voto_popular_sim
            + comparativo.voto_popular_nao
            + comparativo.voto_popular_abstencao
        )
        pct_sim = round(comparativo.voto_popular_sim / total_popular * 100, 1) if total_popular > 0 else 0.0

        result = {
            "proposicao_id": proposicao_id,
            "tipo": proposicao.tipo if proposicao else "?",
            "numero": proposicao.numero if proposicao else 0,
            "ano": proposicao.ano if proposicao else 0,
            "ementa": proposicao.ementa if proposicao else "",
            "voto_popular": {
                "sim": comparativo.voto_popular_sim,
                "nao": comparativo.voto_popular_nao,
                "abstencao": comparativo.voto_popular_abstencao,
                "total": total_popular,
                "percentual_sim": pct_sim,
            },
            "resultado_camara": comparativo.resultado_camara,
            "votos_camara": {
                "sim": comparativo.votos_camara_sim,
                "nao": comparativo.votos_camara_nao,
            },
            "alinhamento": alinhamento_pct,
            "resumo_ia": comparativo.resumo_ia or "",
            "data_geracao": str(comparativo.data_geracao),
        }
        return result
