"""Comparativos endpoints for the parlamentar dashboard.

Provides listing, filtering and evolution of popular-vs-parliamentary
vote comparisons.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.comparativo import ComparativoVotacao
from app.domain.proposicao import Proposicao
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/comparativos", tags=["parlamentar-comparativos"])


# ──────────────────────────────────────────────
#  Response schemas
# ──────────────────────────────────────────────


class ComparativoListItem(BaseModel):
    """A single comparativo with proposição context."""

    id: str
    proposicao_id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    temas: list[str] | None = None
    resultado_camara: str
    voto_popular_sim: int = 0
    voto_popular_nao: int = 0
    voto_popular_abstencao: int = 0
    votos_camara_sim: int = 0
    votos_camara_nao: int = 0
    alinhamento: float = 0.5
    resumo_ia: str | None = None
    data_geracao: str | None = None


class PaginatedComparativos(BaseModel):
    """Paginated comparativos response."""

    total: int
    items: list[ComparativoListItem]
    pagina: int
    itens_por_pagina: int


class EvolucaoAlinhamentoItem(BaseModel):
    """Alinhamento evolution for a time period."""

    mes: str
    alinhamento_medio: float
    total_comparativos: int


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────


@router.get("", response_model=PaginatedComparativos)
async def listar_comparativos(
    alinhamento_min: float | None = Query(None, ge=0.0, le=1.0, description="Alinhamento mínimo"),
    alinhamento_max: float | None = Query(None, ge=0.0, le=1.0, description="Alinhamento máximo"),
    resultado: str | None = Query(None, description="APROVADO ou REJEITADO"),
    tema: str | None = Query(None, description="Filtrar por tema da proposição"),
    ordenar: str = Query("recentes", description="recentes | alinhamento_asc | alinhamento_desc"),
    pagina: int = Query(1, ge=1),
    itens: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> PaginatedComparativos:
    """List comparativos with filters and pagination.

    Joins ComparativoVotacao with Proposicao for context.
    """
    base = (
        select(
            ComparativoVotacao,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            Proposicao.temas,
        )
        .join(Proposicao, ComparativoVotacao.proposicao_id == Proposicao.id)
    )

    # Filters
    if alinhamento_min is not None:
        base = base.where(ComparativoVotacao.alinhamento >= alinhamento_min)
    if alinhamento_max is not None:
        base = base.where(ComparativoVotacao.alinhamento <= alinhamento_max)
    if resultado:
        base = base.where(ComparativoVotacao.resultado_camara == resultado.upper())

    # Tema filter is applied post-query (see below) for cross-DB compatibility
    # PostgreSQL ARRAY and SQLite JSON have different search semantics

    # Count total — need to handle tema filter in Python so first fetch all
    # then post-filter and paginate
    # For non-tema queries, use SQL pagination; for tema queries, do in Python

    if tema:
        # Tema filter requires Python-side filtering for cross-DB compat
        # Ordering
        if ordenar == "alinhamento_asc":
            base = base.order_by(ComparativoVotacao.alinhamento.asc())
        elif ordenar == "alinhamento_desc":
            base = base.order_by(ComparativoVotacao.alinhamento.desc())
        else:
            base = base.order_by(ComparativoVotacao.data_geracao.desc())

        result = await db.execute(base)
        rows = result.all()

        # Filter by tema in Python
        tema_lower = tema.lower()
        filtered = []
        for row in rows:
            temas_parsed = _parse_temas(row.temas)
            if temas_parsed and any(tema_lower in t.lower() for t in temas_parsed):
                filtered.append(row)

        total = len(filtered)
        # Apply pagination
        start = (pagina - 1) * itens
        page_rows = filtered[start:start + itens]
    else:
        # No tema filter — use efficient SQL pagination
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Ordering
        if ordenar == "alinhamento_asc":
            base = base.order_by(ComparativoVotacao.alinhamento.asc())
        elif ordenar == "alinhamento_desc":
            base = base.order_by(ComparativoVotacao.alinhamento.desc())
        else:
            base = base.order_by(ComparativoVotacao.data_geracao.desc())

        base = base.offset((pagina - 1) * itens).limit(itens)

        result = await db.execute(base)
        page_rows = result.all()

    items = []
    for row in page_rows:
        comp = row[0]  # ComparativoVotacao object
        items.append(
            ComparativoListItem(
                id=str(comp.id),
                proposicao_id=comp.proposicao_id,
                tipo=row.tipo,
                numero=row.numero,
                ano=row.ano,
                ementa=row.ementa,
                temas=_parse_temas(row.temas),
                resultado_camara=comp.resultado_camara,
                voto_popular_sim=comp.voto_popular_sim,
                voto_popular_nao=comp.voto_popular_nao,
                voto_popular_abstencao=comp.voto_popular_abstencao,
                votos_camara_sim=comp.votos_camara_sim,
                votos_camara_nao=comp.votos_camara_nao,
                alinhamento=comp.alinhamento,
                resumo_ia=comp.resumo_ia,
                data_geracao=str(comp.data_geracao) if comp.data_geracao else None,
            )
        )

    return PaginatedComparativos(
        total=total,
        items=items,
        pagina=pagina,
        itens_por_pagina=itens,
    )


@router.get("/evolucao", response_model=list[EvolucaoAlinhamentoItem])
async def evolucao_alinhamento(
    meses: int = Query(12, ge=1, le=36, description="Número de meses para evolução"),
    db: AsyncSession = Depends(get_db),
    _current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
) -> list[EvolucaoAlinhamentoItem]:
    """Return monthly average alignment evolution.

    Groups comparativos by month and calculates average alinhamento.
    Fetches all comparativos and groups in Python for cross-DB compat.
    """
    stmt = (
        select(
            ComparativoVotacao.data_geracao,
            ComparativoVotacao.alinhamento,
        )
        .order_by(ComparativoVotacao.data_geracao)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Group in Python by YYYY-MM for cross-DB compatibility
    from collections import defaultdict

    by_month: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.data_geracao is not None:
            mes = row.data_geracao.strftime("%Y-%m")
            by_month[mes].append(float(row.alinhamento or 0.5))

    # Only keep the last N months (most recent)
    months_sorted = sorted(by_month.keys())
    if len(months_sorted) > meses:
        months_sorted = months_sorted[-meses:]

    return [
        EvolucaoAlinhamentoItem(
            mes=mes,
            alinhamento_medio=round(sum(vals) / len(vals), 3),
            total_comparativos=len(vals),
        )
        for mes in months_sorted
        if (vals := by_month[mes])
    ]


def _parse_temas(temas: list[str] | str | None) -> list[str] | None:
    """Parse temas from ARRAY (PG) or JSON string (SQLite)."""
    if temas is None:
        return None
    if isinstance(temas, list):
        return temas
    if isinstance(temas, str):
        import json
        try:
            return json.loads(temas)
        except (json.JSONDecodeError, TypeError):
            return None
    return None
