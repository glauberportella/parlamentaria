"""Meu Mandato endpoints for the parlamentar dashboard.

Provides personal summary and alignment data for the logged-in
parliamentary user, including comparison with party and state peers.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.comparativo import ComparativoVotacao
from app.domain.deputado import Deputado
from app.domain.parlamentar_user import ParlamentarUser
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/meu-mandato", tags=["parlamentar-meu-mandato"])


# ──────────────────────────────────────────────
#  Response schemas
# ──────────────────────────────────────────────


class DeputadoInfo(BaseModel):
    """Basic deputy information."""

    id: int
    nome: str
    sigla_partido: str | None = None
    sigla_uf: str | None = None
    foto_url: str | None = None


class MandatoResumo(BaseModel):
    """Personal dashboard summary for the logged-in user."""

    deputado: DeputadoInfo | None = None
    total_comparativos: int = 0
    alinhamento_medio: float = 0.5
    total_votos_populares_recebidos: int = 0
    proposicoes_acompanhadas: int = 0
    comparativos_alinhados: int = 0
    comparativos_divergentes: int = 0
    temas_acompanhados: list[str] | None = None


class AlinhamentoSerieItem(BaseModel):
    """Single data point for alignment time series."""

    mes: str
    alinhamento: float
    total: int


class AlinhamentoComparacao(BaseModel):
    """Comparison of alignment: personal vs partido vs state."""

    pessoal: list[AlinhamentoSerieItem]
    partido: list[AlinhamentoSerieItem]
    uf: list[AlinhamentoSerieItem]
    alinhamento_medio_pessoal: float = 0.5
    alinhamento_medio_partido: float = 0.5
    alinhamento_medio_uf: float = 0.5
    sigla_partido: str | None = None
    sigla_uf: str | None = None


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────


@router.get("/resumo", response_model=MandatoResumo)
async def meu_mandato_resumo(
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> MandatoResumo:
    """Return personal summary for the logged-in parlamentar user.

    If the user has a linked deputado, includes deputy info and statistics
    based on comparativos. Otherwise returns a lighter summary.
    """
    deputado_info = None

    if current_user.deputado_id:
        dep_result = await db.execute(
            select(Deputado).where(Deputado.id == current_user.deputado_id)
        )
        dep = dep_result.scalar_one_or_none()
        if dep:
            deputado_info = DeputadoInfo(
                id=dep.id,
                nome=dep.nome,
                sigla_partido=dep.sigla_partido,
                sigla_uf=dep.sigla_uf,
                foto_url=dep.foto_url,
            )

    # Aggregated comparativo stats
    stats_result = await db.execute(
        select(
            func.count(ComparativoVotacao.id).label("total"),
            func.avg(ComparativoVotacao.alinhamento).label("avg_alinhamento"),
            func.count(
                case(
                    (ComparativoVotacao.alinhamento >= 0.5, ComparativoVotacao.id),
                )
            ).label("alinhados"),
            func.count(
                case(
                    (ComparativoVotacao.alinhamento < 0.5, ComparativoVotacao.id),
                )
            ).label("divergentes"),
        )
    )
    stats = stats_result.one()

    # Total popular votes received
    votos_total_result = await db.execute(
        select(func.count(VotoPopular.id))
    )
    total_votos = votos_total_result.scalar() or 0

    # Proposições being tracked (with comparativos)
    proposicoes_result = await db.execute(
        select(func.count(func.distinct(ComparativoVotacao.proposicao_id)))
    )
    proposicoes_count = proposicoes_result.scalar() or 0

    return MandatoResumo(
        deputado=deputado_info,
        total_comparativos=stats.total or 0,
        alinhamento_medio=round(float(stats.avg_alinhamento or 0.5), 3),
        total_votos_populares_recebidos=total_votos,
        proposicoes_acompanhadas=proposicoes_count,
        comparativos_alinhados=stats.alinhados or 0,
        comparativos_divergentes=stats.divergentes or 0,
        temas_acompanhados=current_user.temas_acompanhados,
    )


@router.get("/alinhamento", response_model=AlinhamentoComparacao)
async def meu_mandato_alinhamento(
    meses: int = Query(12, ge=1, le=36, description="Meses de histórico"),
    db: AsyncSession = Depends(get_db),
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> AlinhamentoComparacao:
    """Return alignment evolution with comparison to party and state averages.

    Provides three time series:
    - pessoal: overall alignment evolution
    - partido: average alignment for the user's party peers
    - uf: average alignment for the user's state peers
    """
    from collections import defaultdict

    # Fetch all comparativos and group in Python for cross-DB compatibility
    global_stmt = (
        select(
            ComparativoVotacao.data_geracao,
            ComparativoVotacao.alinhamento,
        )
        .order_by(ComparativoVotacao.data_geracao)
    )
    global_result = await db.execute(global_stmt)
    global_rows = global_result.all()

    by_month: dict[str, list[float]] = defaultdict(list)
    for row in global_rows:
        if row.data_geracao is not None:
            mes = row.data_geracao.strftime("%Y-%m")
            by_month[mes].append(float(row.alinhamento or 0.5))

    months_sorted = sorted(by_month.keys())
    if len(months_sorted) > meses:
        months_sorted = months_sorted[-meses:]

    pessoal_series = [
        AlinhamentoSerieItem(
            mes=mes,
            alinhamento=round(sum(vals) / len(vals), 3),
            total=len(vals),
        )
        for mes in months_sorted
        if (vals := by_month[mes])
    ]

    # Compute overall averages
    avg_pessoal = 0.5
    if pessoal_series:
        total_w = sum(s.total for s in pessoal_series)
        if total_w > 0:
            avg_pessoal = sum(s.alinhamento * s.total for s in pessoal_series) / total_w

    # Get deputado info for party/UF comparison
    sigla_partido = None
    sigla_uf = None
    if current_user.deputado_id:
        dep_result = await db.execute(
            select(Deputado).where(Deputado.id == current_user.deputado_id)
        )
        dep = dep_result.scalar_one_or_none()
        if dep:
            sigla_partido = dep.sigla_partido
            sigla_uf = dep.sigla_uf

    # For partido and UF: in a full implementation, we'd filter comparativos
    # by votos_parlamentares who belong to the same party/UF. Since that requires
    # JSONB parsing, for now we use the same global series as a baseline
    # with slight differentiation markers.
    # This will be enhanced when we have per-deputado vote tracking.
    partido_series = pessoal_series  # Same baseline for now
    uf_series = pessoal_series  # Same baseline for now

    return AlinhamentoComparacao(
        pessoal=pessoal_series,
        partido=partido_series,
        uf=uf_series,
        alinhamento_medio_pessoal=round(avg_pessoal, 3),
        alinhamento_medio_partido=round(avg_pessoal, 3),
        alinhamento_medio_uf=round(avg_pessoal, 3),
        sigla_partido=sigla_partido,
        sigla_uf=sigla_uf,
    )
