"""Dashboard data endpoints for the parliamentarian dashboard.

Provides aggregated KPIs, charts, alerts, and ranking data.
Response format aligns exactly with the frontend TypeScript types.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.comparativo import ComparativoVotacao
from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.voto_popular import VotoPopular
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["parlamentar-dashboard"])


# ──────────────────────────────────────────────
#  Response schemas — aligned with frontend types
# ──────────────────────────────────────────────


class DashboardKPIs(BaseModel):
    """KPIs matching frontend DashboardKPIs type."""

    total_proposicoes_ativas: int = 0
    total_eleitores_cadastrados: int = 0
    total_votos_populares: int = 0
    total_comparativos: int = 0
    alinhamento_medio: float = 0.0
    taxa_participacao: float = 0.0


class ProposicaoRankingItem(BaseModel):
    """Proposição ranking matching frontend ProposicaoRanking type."""

    proposicao_id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    total_votos: int
    percentual_sim: float
    percentual_nao: float
    alinhamento: float | None = None


class TemaAtivoItem(BaseModel):
    """Active tema matching frontend TemaAtivo type."""

    tema: str
    total_votos: int
    total_proposicoes: int = 0


class DashboardTendencias(BaseModel):
    """Tendências matching frontend DashboardTendencias type."""

    votos_ultimos_7_dias: int = 0
    novos_eleitores_ultimos_7_dias: int = 0
    proposicoes_mais_votadas: list[ProposicaoRankingItem] = []
    temas_mais_ativos: list[TemaAtivoItem] = []


class DashboardAlertaItem(BaseModel):
    """Alert matching frontend DashboardAlerta type."""

    tipo: str
    mensagem: str
    urgencia: str = "media"  # alta, media, baixa


class DashboardResumo(BaseModel):
    """Complete dashboard summary matching frontend DashboardResumo type."""

    kpis: DashboardKPIs
    tendencias: DashboardTendencias
    alertas: list[DashboardAlertaItem]


# ──────────────────────────────────────────────
#  Endpoint
# ──────────────────────────────────────────────


@router.get("/resumo", response_model=DashboardResumo)
async def get_dashboard_resumo(
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResumo:
    """Aggregated dashboard data: KPIs, tendências, and alerts."""
    now = datetime.now(timezone.utc)
    period_30d = now - timedelta(days=30)
    period_7d = now - timedelta(days=7)

    # ── KPI queries ──

    total_proposicoes = (
        await db.execute(select(func.count(Proposicao.id)))
    ).scalar() or 0

    total_eleitores = (
        await db.execute(select(func.count(Eleitor.id)))
    ).scalar() or 0

    total_votos = (
        await db.execute(select(func.count(VotoPopular.id)))
    ).scalar() or 0

    total_comparativos = (
        await db.execute(select(func.count(ComparativoVotacao.id)))
    ).scalar() or 0

    alinhamento_medio = round(
        float(
            (
                await db.execute(
                    select(func.avg(ComparativoVotacao.alinhamento))
                )
            ).scalar()
            or 0.0
        ),
        2,
    )

    # Taxa de participação: eleitores com pelo menos 1 voto / total eleitores
    eleitores_votantes = (
        await db.execute(
            select(func.count(func.distinct(VotoPopular.eleitor_id)))
        )
    ).scalar() or 0
    taxa_participacao = (
        round(eleitores_votantes / total_eleitores, 2)
        if total_eleitores > 0
        else 0.0
    )

    kpis = DashboardKPIs(
        total_proposicoes_ativas=total_proposicoes,
        total_eleitores_cadastrados=total_eleitores,
        total_votos_populares=total_votos,
        total_comparativos=total_comparativos,
        alinhamento_medio=alinhamento_medio,
        taxa_participacao=taxa_participacao,
    )

    # ── Tendências (últimos 7 dias) ──

    votos_7d = (
        await db.execute(
            select(func.count(VotoPopular.id)).where(
                VotoPopular.data_voto >= period_7d
            )
        )
    ).scalar() or 0

    novos_eleitores_7d = (
        await db.execute(
            select(func.count(Eleitor.id)).where(Eleitor.data_cadastro >= period_7d)
        )
    ).scalar() or 0

    # ── Temas mais ativos (últimos 30 dias) ──

    temas_ativos: list[TemaAtivoItem] = []
    try:
        temas_query = (
            select(
                func.unnest(Proposicao.temas).label("tema"),
                func.count(func.distinct(VotoPopular.id)).label("total_votos"),
                func.count(func.distinct(Proposicao.id)).label("total_proposicoes"),
            )
            .join(VotoPopular, VotoPopular.proposicao_id == Proposicao.id)
            .where(VotoPopular.data_voto >= period_30d)
            .group_by("tema")
            .order_by(desc("total_votos"))
            .limit(10)
        )
        temas_result = await db.execute(temas_query)
        temas_ativos = [
            TemaAtivoItem(
                tema=row.tema,
                total_votos=row.total_votos,
                total_proposicoes=row.total_proposicoes,
            )
            for row in temas_result.all()
        ]
    except Exception:
        logger.warning("dashboard.temas_query_failed")

    # ── Proposições ranking (top 10 por total de votos) ──

    proposicoes_ranking: list[ProposicaoRankingItem] = []
    try:
        ranking_query = (
            select(
                Proposicao.id,
                Proposicao.tipo,
                Proposicao.numero,
                Proposicao.ano,
                Proposicao.ementa,
                func.count(VotoPopular.id).label("total_votos"),
                func.round(
                    100.0
                    * func.sum(case((VotoPopular.voto == "SIM", 1), else_=0))
                    / func.greatest(func.count(VotoPopular.id), 1),
                    1,
                ).label("percentual_sim"),
                func.round(
                    100.0
                    * func.sum(case((VotoPopular.voto == "NAO", 1), else_=0))
                    / func.greatest(func.count(VotoPopular.id), 1),
                    1,
                ).label("percentual_nao"),
            )
            .join(VotoPopular, VotoPopular.proposicao_id == Proposicao.id)
            .group_by(Proposicao.id)
            .order_by(desc("total_votos"))
            .limit(10)
        )
        ranking_result = await db.execute(ranking_query)
        proposicoes_ranking = [
            ProposicaoRankingItem(
                proposicao_id=row.id,
                tipo=row.tipo,
                numero=row.numero,
                ano=row.ano,
                ementa=row.ementa[:200] if row.ementa else "",
                total_votos=row.total_votos,
                percentual_sim=float(row.percentual_sim or 0),
                percentual_nao=float(row.percentual_nao or 0),
            )
            for row in ranking_result.all()
        ]
    except Exception:
        logger.warning("dashboard.ranking_query_failed")

    tendencias = DashboardTendencias(
        votos_ultimos_7_dias=votos_7d,
        novos_eleitores_ultimos_7_dias=novos_eleitores_7d,
        proposicoes_mais_votadas=proposicoes_ranking,
        temas_mais_ativos=temas_ativos,
    )

    # ── Alertas recentes ──

    alertas: list[DashboardAlertaItem] = []
    try:
        recent_votacoes = await db.execute(
            select(Votacao)
            .where(Votacao.data >= period_30d)
            .order_by(desc(Votacao.data))
            .limit(5)
        )
        for votacao in recent_votacoes.scalars().all():
            resultado = (
                "Aprovado"
                if votacao.aprovacao
                else "Rejeitado" if votacao.aprovacao is False else "Pendente"
            )
            alertas.append(
                DashboardAlertaItem(
                    tipo="nova_votacao",
                    mensagem=f"{votacao.descricao[:80] if votacao.descricao else 'Votação'} — {resultado}",
                    urgencia=(
                        "alta"
                        if votacao.data >= now - timedelta(days=2)
                        else "media"
                    ),
                )
            )

        recent_comparativos = await db.execute(
            select(ComparativoVotacao)
            .where(ComparativoVotacao.data_geracao >= period_30d)
            .order_by(desc(ComparativoVotacao.data_geracao))
            .limit(3)
        )
        for comp in recent_comparativos.scalars().all():
            alinhamento_pct = (
                round(comp.alinhamento * 100, 1) if comp.alinhamento else 0
            )
            alertas.append(
                DashboardAlertaItem(
                    tipo="comparativo",
                    mensagem=f"Comparativo Proposição {comp.proposicao_id} — Alinhamento: {alinhamento_pct}%",
                    urgencia="baixa",
                )
            )
    except Exception:
        logger.warning("dashboard.alertas_query_failed")

    return DashboardResumo(
        kpis=kpis,
        tendencias=tendencias,
        alertas=alertas,
    )
