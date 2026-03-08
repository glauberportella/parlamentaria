"""Dashboard data endpoints for the parliamentarian dashboard.

Provides aggregated KPIs, charts, alerts, and ranking data.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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
#  Response schemas
# ──────────────────────────────────────────────


class KpiData(BaseModel):
    """Key performance indicators for the dashboard."""

    total_proposicoes: int = 0
    total_eleitores: int = 0
    total_votos: int = 0
    alinhamento_medio: float = 0.0
    proposicoes_delta: int = Field(0, description="Variação vs período anterior")
    eleitores_delta: int = Field(0, description="Novos eleitores no período")
    votos_delta: int = Field(0, description="Votos no período")


class TemaAtivo(BaseModel):
    """Active tema with vote count."""

    tema: str
    contagem: int


class ProposicaoRanking(BaseModel):
    """Proposição ranked by popular votes."""

    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    total_votos: int
    percentual_sim: float
    percentual_nao: float
    alinhamento: float | None = None


class AlertaItem(BaseModel):
    """A dashboard alert."""

    id: str
    titulo: str
    descricao: str
    urgencia: str = "media"  # alta, media, baixa
    data: datetime


class DashboardResumo(BaseModel):
    """Complete dashboard summary for the parlamentar."""

    kpis: KpiData
    temas_ativos: list[TemaAtivo]
    proposicoes_ranking: list[ProposicaoRanking]
    alertas: list[AlertaItem]


# ──────────────────────────────────────────────
#  Endpoint
# ──────────────────────────────────────────────


@router.get("/resumo", response_model=DashboardResumo)
async def get_dashboard_resumo(
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResumo:
    """Aggregated dashboard data: KPIs, themes, ranking, and alerts."""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=30)
    prev_period_start = period_start - timedelta(days=30)

    # ── KPI queries ──

    # Total proposições
    total_prop_result = await db.execute(select(func.count(Proposicao.id)))
    total_proposicoes = total_prop_result.scalar() or 0

    # Proposições no período (delta)
    prop_delta_result = await db.execute(
        select(func.count(Proposicao.id)).where(
            Proposicao.data_apresentacao >= period_start.date()
        )
    )
    proposicoes_delta = prop_delta_result.scalar() or 0

    # Total eleitores
    total_eleitores_result = await db.execute(select(func.count(Eleitor.id)))
    total_eleitores = total_eleitores_result.scalar() or 0

    # Novos eleitores no período
    eleitores_delta_result = await db.execute(
        select(func.count(Eleitor.id)).where(Eleitor.data_cadastro >= period_start)
    )
    eleitores_delta = eleitores_delta_result.scalar() or 0

    # Total votos populares
    total_votos_result = await db.execute(select(func.count(VotoPopular.id)))
    total_votos = total_votos_result.scalar() or 0

    # Votos no período
    votos_delta_result = await db.execute(
        select(func.count(VotoPopular.id)).where(
            VotoPopular.data_voto >= period_start
        )
    )
    votos_delta = votos_delta_result.scalar() or 0

    # Alinhamento médio (dos comparativos existentes)
    alinhamento_result = await db.execute(
        select(func.avg(ComparativoVotacao.alinhamento))
    )
    alinhamento_medio = round(float(alinhamento_result.scalar() or 0.0), 2)

    kpis = KpiData(
        total_proposicoes=total_proposicoes,
        total_eleitores=total_eleitores,
        total_votos=total_votos,
        alinhamento_medio=alinhamento_medio,
        proposicoes_delta=proposicoes_delta,
        eleitores_delta=eleitores_delta,
        votos_delta=votos_delta,
    )

    # ── Temas ativos (top 10 por votos nos últimos 30 dias) ──

    temas_ativos: list[TemaAtivo] = []
    try:
        # Proposições have temas as ARRAY — we unnest and count votos
        temas_query = (
            select(
                func.unnest(Proposicao.temas).label("tema"),
                func.count(VotoPopular.id).label("contagem"),
            )
            .join(VotoPopular, VotoPopular.proposicao_id == Proposicao.id)
            .where(VotoPopular.data_voto >= period_start)
            .group_by("tema")
            .order_by(desc("contagem"))
            .limit(10)
        )
        temas_result = await db.execute(temas_query)
        temas_ativos = [
            TemaAtivo(tema=row.tema, contagem=row.contagem)
            for row in temas_result.all()
        ]
    except Exception:
        logger.warning("dashboard.temas_query_failed")

    # ── Proposições ranking (top 10 por total de votos) ──

    proposicoes_ranking: list[ProposicaoRanking] = []
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
                    * func.sum(
                        case((VotoPopular.voto == "SIM", 1), else_=0)
                    )
                    / func.greatest(func.count(VotoPopular.id), 1),
                    1,
                ).label("percentual_sim"),
                func.round(
                    100.0
                    * func.sum(
                        case((VotoPopular.voto == "NAO", 1), else_=0)
                    )
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
            ProposicaoRanking(
                id=row.id,
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

    # ── Alertas recentes ──

    alertas: list[AlertaItem] = []
    try:
        # Votações recentes que não têm voto popular (oportunidade de engajamento)
        recent_votacoes = await db.execute(
            select(Votacao)
            .where(Votacao.data >= period_start)
            .order_by(desc(Votacao.data))
            .limit(5)
        )
        for votacao in recent_votacoes.scalars().all():
            alertas.append(
                AlertaItem(
                    id=str(votacao.id),
                    titulo=f"Votação: {votacao.descricao[:80] if votacao.descricao else 'Sem descrição'}",
                    descricao=f"Resultado: {'Aprovado' if votacao.aprovacao else 'Rejeitado' if votacao.aprovacao is False else 'Pendente'}",
                    urgencia="alta" if votacao.data >= now - timedelta(days=2) else "media",
                    data=votacao.data,
                )
            )

        # Novos comparativos
        recent_comparativos = await db.execute(
            select(ComparativoVotacao)
            .where(ComparativoVotacao.data_geracao >= period_start)
            .order_by(desc(ComparativoVotacao.data_geracao))
            .limit(3)
        )
        for comp in recent_comparativos.scalars().all():
            alinhamento_pct = round(comp.alinhamento * 100, 1) if comp.alinhamento else 0
            alertas.append(
                AlertaItem(
                    id=str(comp.id),
                    titulo=f"Comparativo: Proposição {comp.proposicao_id}",
                    descricao=f"Alinhamento popular: {alinhamento_pct}%",
                    urgencia="baixa",
                    data=comp.data_geracao,
                )
            )
    except Exception:
        logger.warning("dashboard.alertas_query_failed")

    return DashboardResumo(
        kpis=kpis,
        temas_ativos=temas_ativos,
        proposicoes_ranking=proposicoes_ranking,
        alertas=alertas,
    )
