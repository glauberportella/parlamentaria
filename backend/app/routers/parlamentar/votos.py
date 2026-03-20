"""Votos analíticos endpoints for the parlamentar dashboard.

Provides aggregated vote analytics: breakdown by tema, by UF,
timeline series, and ranking of most-voted proposições.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

# Premium plan gate — only enforced when parlamentaria-premium is installed
try:
    from premium.billing.gabinete_gate import require_gabinete_plan

    _require_pro = require_gabinete_plan("gabinete_pro", "gabinete_enterprise")
except ImportError:
    _require_pro = get_current_parlamentar_user

logger = get_logger(__name__)

router = APIRouter(prefix="/votos", tags=["parlamentar-votos"])


# ──────────────────────────────────────────────
#  Response schemas
# ──────────────────────────────────────────────


class VotosPorTemaItem(BaseModel):
    """Vote breakdown for a single tema."""

    tema: str
    total_votos: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0


class VotosPorUFItem(BaseModel):
    """Vote breakdown for a single UF (state)."""

    uf: str
    total_votos: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0


class VotosTimelineItem(BaseModel):
    """Vote aggregation for a single date."""

    data: str
    total_votos: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0


class VotosRankingItem(BaseModel):
    """Proposição ranked by total votes."""

    proposicao_id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    total_votos: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0
    percentual_sim: float = 0.0
    percentual_nao: float = 0.0


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────


@router.get("/por-tema", response_model=list[VotosPorTemaItem])
async def votos_por_tema(
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> list[VotosPorTemaItem]:
    """Aggregate popular votes grouped by proposição tema.

    Unnests the temas ARRAY from proposições, then groups votes by each tema.
    Returns a list sorted by total_votos descending.
    """
    # Build a CTE that maps each voto to its proposição's temas
    # For SQLite compatibility we join VotoPopular → Proposicao and use temas directly.
    # In PostgreSQL we'd use func.unnest(Proposicao.temas), but for SQLite (tests)
    # we query proposições with their temas and manually aggregate in Python.

    stmt = (
        select(
            Proposicao.temas,
            func.count(VotoPopular.id).label("total_votos"),
            func.count(case((VotoPopular.voto == VotoEnum.SIM, 1))).label("sim"),
            func.count(case((VotoPopular.voto == VotoEnum.NAO, 1))).label("nao"),
            func.count(case((VotoPopular.voto == VotoEnum.ABSTENCAO, 1))).label("abstencao"),
        )
        .join(Proposicao, VotoPopular.proposicao_id == Proposicao.id)
        .group_by(Proposicao.id)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Manually unnest temas (works with both PostgreSQL ARRAY and SQLite JSON)
    tema_agg: dict[str, dict[str, int]] = {}
    for row in rows:
        temas = row.temas or []
        # SQLite stores ARRAY as JSON string; handle both list and None
        if isinstance(temas, str):
            import json
            try:
                temas = json.loads(temas)
            except (json.JSONDecodeError, TypeError):
                temas = []

        for tema in temas:
            if tema not in tema_agg:
                tema_agg[tema] = {"total_votos": 0, "sim": 0, "nao": 0, "abstencao": 0}
            tema_agg[tema]["total_votos"] += row.total_votos
            tema_agg[tema]["sim"] += row.sim
            tema_agg[tema]["nao"] += row.nao
            tema_agg[tema]["abstencao"] += row.abstencao

    items = [
        VotosPorTemaItem(tema=tema, **counts)
        for tema, counts in tema_agg.items()
    ]
    items.sort(key=lambda x: x.total_votos, reverse=True)
    return items


@router.get("/por-uf", response_model=list[VotosPorUFItem])
async def votos_por_uf(
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(_require_pro),
) -> list[VotosPorUFItem]:
    """Aggregate popular votes grouped by eleitor UF (state).

    Joins VotoPopular → Eleitor and groups by UF.
    Returns list sorted by total_votos descending.
    """
    stmt = (
        select(
            Eleitor.uf,
            func.count(VotoPopular.id).label("total_votos"),
            func.count(case((VotoPopular.voto == VotoEnum.SIM, 1))).label("sim"),
            func.count(case((VotoPopular.voto == VotoEnum.NAO, 1))).label("nao"),
            func.count(case((VotoPopular.voto == VotoEnum.ABSTENCAO, 1))).label("abstencao"),
        )
        .join(Eleitor, VotoPopular.eleitor_id == Eleitor.id)
        .group_by(Eleitor.uf)
        .order_by(desc("total_votos"))
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        VotosPorUFItem(
            uf=row.uf,
            total_votos=row.total_votos,
            sim=row.sim,
            nao=row.nao,
            abstencao=row.abstencao,
        )
        for row in rows
    ]


@router.get("/timeline", response_model=list[VotosTimelineItem])
async def votos_timeline(
    dias: int = Query(default=30, ge=1, le=365, description="Número de dias para o histórico"),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> list[VotosTimelineItem]:
    """Aggregate popular votes by date over the last N days.

    Returns a daily breakdown suitable for timeline charts.
    Sorted by date ascending.
    """
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=dias)

    # Use func.date() which works on both PostgreSQL and SQLite
    vote_date = func.date(VotoPopular.data_voto)

    stmt = (
        select(
            vote_date.label("data"),
            func.count(VotoPopular.id).label("total_votos"),
            func.count(case((VotoPopular.voto == VotoEnum.SIM, 1))).label("sim"),
            func.count(case((VotoPopular.voto == VotoEnum.NAO, 1))).label("nao"),
            func.count(case((VotoPopular.voto == VotoEnum.ABSTENCAO, 1))).label("abstencao"),
        )
        .where(VotoPopular.data_voto >= cutoff)
        .group_by(vote_date)
        .order_by(vote_date)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        VotosTimelineItem(
            data=str(row.data) if row.data else "",
            total_votos=row.total_votos,
            sim=row.sim,
            nao=row.nao,
            abstencao=row.abstencao,
        )
        for row in rows
    ]


@router.get("/ranking", response_model=list[VotosRankingItem])
async def votos_ranking(
    limite: int = Query(default=10, ge=1, le=50, description="Número de proposições no ranking"),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> list[VotosRankingItem]:
    """Rank proposições by total popular votes (descending).

    Returns the top N most-voted proposições with vote breakdown.
    """
    stmt = (
        select(
            Proposicao.id.label("proposicao_id"),
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            func.count(VotoPopular.id).label("total_votos"),
            func.count(case((VotoPopular.voto == VotoEnum.SIM, 1))).label("sim"),
            func.count(case((VotoPopular.voto == VotoEnum.NAO, 1))).label("nao"),
            func.count(case((VotoPopular.voto == VotoEnum.ABSTENCAO, 1))).label("abstencao"),
        )
        .join(VotoPopular, VotoPopular.proposicao_id == Proposicao.id)
        .group_by(Proposicao.id, Proposicao.tipo, Proposicao.numero, Proposicao.ano, Proposicao.ementa)
        .order_by(desc("total_votos"))
        .limit(limite)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items: list[VotosRankingItem] = []
    for row in rows:
        total = row.total_votos or 1
        items.append(
            VotosRankingItem(
                proposicao_id=row.proposicao_id,
                tipo=row.tipo,
                numero=row.numero,
                ano=row.ano,
                ementa=row.ementa,
                total_votos=row.total_votos,
                sim=row.sim,
                nao=row.nao,
                abstencao=row.abstencao,
                percentual_sim=round(row.sim / total * 100, 1),
                percentual_nao=round(row.nao / total * 100, 1),
            )
        )
    return items
