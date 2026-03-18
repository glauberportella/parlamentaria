"""Public citizen-facing endpoints — read-only, no authentication.

Exposes aggregated legislative data (proposições, popular votes,
comparativos) for consumption by the public Parlamentaria site.
All data is anonymized and aggregated — no individual voter data exposed.
"""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Numeric, asc, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.dependencies import get_db
from app.domain.analise_ia import AnaliseIA
from app.domain.comparativo import ComparativoVotacao
from app.domain.eleitor import Eleitor
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoEnum, VotoPopular
from app.logging import get_logger
from app.middleware import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/cidadao", tags=["cidadao"])


# ──────────────────────────────────────────────
#  Response schemas — public subset
# ──────────────────────────────────────────────


class VotoPopularResumo(BaseModel):
    """Aggregated vote summary for a proposição."""

    total: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0
    percentual_sim: float = 0.0
    percentual_nao: float = 0.0
    percentual_abstencao: float = 0.0


class CidadaoKPIs(BaseModel):
    """Public KPIs for the citizen panel."""

    total_proposicoes: int = 0
    total_eleitores: int = 0
    total_votos: int = 0
    total_comparativos: int = 0
    alinhamento_medio: float = 0.0


class ProposicaoRankingItem(BaseModel):
    """Top-voted proposição for public ranking."""

    proposicao_id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    total_votos: int
    percentual_sim: float
    percentual_nao: float


class TemaAtivoItem(BaseModel):
    """Active tema with vote counts."""

    tema: str
    total_votos: int
    total_proposicoes: int = 0


class VotosTimelineItem(BaseModel):
    """Daily vote aggregation for timeline charts."""

    data: str
    total_votos: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0


class CidadaoResumo(BaseModel):
    """Complete public overview for citizen panel."""

    kpis: CidadaoKPIs
    proposicoes_mais_votadas: list[ProposicaoRankingItem]
    temas_ativos: list[TemaAtivoItem]
    timeline_30d: list[VotosTimelineItem]


class CidadaoProposicaoListItem(BaseModel):
    """Proposição item for public listing."""

    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    situacao: str | None = None
    temas: list[str] | None = None
    data_apresentacao: str | None = None
    resumo_ia: str | None = None
    votos: VotoPopularResumo
    tem_analise: bool = False
    tem_comparativo: bool = False


class PaginatedProposicoes(BaseModel):
    """Paginated proposições response."""

    total: int
    items: list[CidadaoProposicaoListItem]
    pagina: int
    itens_por_pagina: int


class AnaliseIAPublica(BaseModel):
    """Public subset of AI analysis."""

    resumo_leigo: str
    impacto_esperado: str
    areas_afetadas: list[str]
    argumentos_favor: list[str]
    argumentos_contra: list[str]


class ComparativoPublico(BaseModel):
    """Public comparativo summary."""

    resultado_camara: str
    votos_camara_sim: int
    votos_camara_nao: int
    alinhamento: float
    resumo_ia: str | None = None


class CidadaoProposicaoDetalhe(BaseModel):
    """Full public proposição detail."""

    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    situacao: str | None = None
    temas: list[str] | None = None
    data_apresentacao: str | None = None
    resumo_ia: str | None = None
    votos: VotoPopularResumo
    analise: AnaliseIAPublica | None = None
    comparativo: ComparativoPublico | None = None


class VotosPorTemaItem(BaseModel):
    """Vote breakdown by tema."""

    tema: str
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


class ComparativoListItem(BaseModel):
    """Public comparativo list item."""

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
    """Monthly alignment evolution."""

    mes: str
    alinhamento_medio: float
    total_comparativos: int


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────


def _build_voto_resumo(
    total: int, sim: int, nao: int, abstencao: int,
) -> VotoPopularResumo:
    """Build VotoPopularResumo with safe percentage calculation."""
    if total == 0:
        return VotoPopularResumo()
    return VotoPopularResumo(
        total=total,
        sim=sim,
        nao=nao,
        abstencao=abstencao,
        percentual_sim=round(100.0 * sim / total, 1),
        percentual_nao=round(100.0 * nao / total, 1),
        percentual_abstencao=round(100.0 * abstencao / total, 1),
    )


def _parse_temas(temas: list[str] | str | None) -> list[str] | None:
    """Parse temas from ARRAY (PG) or JSON string (SQLite)."""
    if temas is None:
        return None
    if isinstance(temas, list):
        return temas
    if isinstance(temas, str):
        try:
            return json.loads(temas)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────


@router.get("/resumo", response_model=CidadaoResumo)
@limiter.limit("60/minute")
async def get_cidadao_resumo(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CidadaoResumo:
    """Public overview: KPIs, top proposições, active temas, and 30-day timeline."""
    now = datetime.now(UTC)
    period_30d = now - timedelta(days=30)

    # ── KPIs ──
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
            (await db.execute(
                select(func.avg(ComparativoVotacao.alinhamento))
            )).scalar() or 0.0
        ),
        2,
    )

    kpis = CidadaoKPIs(
        total_proposicoes=total_proposicoes,
        total_eleitores=total_eleitores,
        total_votos=total_votos,
        total_comparativos=total_comparativos,
        alinhamento_medio=alinhamento_medio,
    )

    # ── Top 10 most-voted proposições ──
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
                    cast(
                        100.0
                        * func.sum(case((VotoPopular.voto == "SIM", 1), else_=0))
                        / func.greatest(func.count(VotoPopular.id), 1),
                        Numeric,
                    ),
                    1,
                ).label("percentual_sim"),
                func.round(
                    cast(
                        100.0
                        * func.sum(case((VotoPopular.voto == "NAO", 1), else_=0))
                        / func.greatest(func.count(VotoPopular.id), 1),
                        Numeric,
                    ),
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
        logger.warning("cidadao.ranking_query_failed")

    # ── Active temas (last 30 days) ──
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
        logger.warning("cidadao.temas_query_failed")

    # ── Timeline (last 30 days) ──
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    vote_date = func.date(VotoPopular.data_voto)

    timeline_stmt = (
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
    timeline_result = await db.execute(timeline_stmt)
    timeline = [
        VotosTimelineItem(
            data=str(row.data) if row.data else "",
            total_votos=row.total_votos,
            sim=row.sim,
            nao=row.nao,
            abstencao=row.abstencao,
        )
        for row in timeline_result.all()
    ]

    return CidadaoResumo(
        kpis=kpis,
        proposicoes_mais_votadas=proposicoes_ranking,
        temas_ativos=temas_ativos,
        timeline_30d=timeline,
    )


@router.get("/proposicoes", response_model=PaginatedProposicoes)
@limiter.limit("60/minute")
async def listar_proposicoes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tema: str | None = Query(None, description="Filtrar por tema"),
    tipo: str | None = Query(None, description="Filtrar por tipo (PL, PEC, MPV...)"),
    ano: int | None = Query(None, description="Filtrar por ano"),
    busca: str | None = Query(None, description="Busca por texto na ementa"),
    ordenar: str = Query("recentes", description="recentes | votos_desc | votos_asc"),
    pagina: int = Query(1, ge=1),
    itens: int = Query(20, ge=1, le=100),
) -> PaginatedProposicoes:
    """Public paginated proposição listing with vote summaries."""

    # ── Vote aggregation subquery ──
    vote_subq = (
        select(
            VotoPopular.proposicao_id,
            func.count(VotoPopular.id).label("total_votos"),
            func.sum(case((VotoPopular.voto == "SIM", 1), else_=0)).label("votos_sim"),
            func.sum(case((VotoPopular.voto == "NAO", 1), else_=0)).label("votos_nao"),
            func.sum(case((VotoPopular.voto == "ABSTENCAO", 1), else_=0)).label("votos_abstencao"),
        )
        .group_by(VotoPopular.proposicao_id)
        .subquery()
    )

    analise_subq = (
        select(
            AnaliseIA.proposicao_id,
            func.count(AnaliseIA.id).label("tem_analise"),
        )
        .group_by(AnaliseIA.proposicao_id)
        .subquery()
    )

    comparativo_subq = (
        select(
            ComparativoVotacao.proposicao_id,
            func.count(ComparativoVotacao.id).label("tem_comparativo"),
        )
        .group_by(ComparativoVotacao.proposicao_id)
        .subquery()
    )

    # ── Filters ──
    base_filter = select(Proposicao)
    if tema:
        base_filter = base_filter.where(Proposicao.temas.any(tema))
    if tipo:
        base_filter = base_filter.where(Proposicao.tipo == tipo.upper())
    if ano:
        base_filter = base_filter.where(Proposicao.ano == ano)
    if busca:
        base_filter = base_filter.where(Proposicao.ementa.ilike(f"%{busca}%"))

    # ── Count ──
    count_query = select(func.count()).select_from(base_filter.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # ── Main query with joins ──
    main_query = (
        base_filter.outerjoin(vote_subq, vote_subq.c.proposicao_id == Proposicao.id)
        .outerjoin(analise_subq, analise_subq.c.proposicao_id == Proposicao.id)
        .outerjoin(comparativo_subq, comparativo_subq.c.proposicao_id == Proposicao.id)
        .add_columns(
            func.coalesce(vote_subq.c.total_votos, 0).label("total_votos"),
            func.coalesce(vote_subq.c.votos_sim, 0).label("votos_sim"),
            func.coalesce(vote_subq.c.votos_nao, 0).label("votos_nao"),
            func.coalesce(vote_subq.c.votos_abstencao, 0).label("votos_abstencao"),
            func.coalesce(analise_subq.c.tem_analise, 0).label("tem_analise"),
            func.coalesce(comparativo_subq.c.tem_comparativo, 0).label("tem_comparativo"),
        )
    )

    # ── Ordering ──
    if ordenar == "votos_desc":
        main_query = main_query.order_by(desc("total_votos"), desc(Proposicao.id))
    elif ordenar == "votos_asc":
        main_query = main_query.order_by(asc("total_votos"), desc(Proposicao.id))
    else:
        main_query = main_query.order_by(desc(Proposicao.id))

    main_query = main_query.offset((pagina - 1) * itens).limit(itens)
    result = await db.execute(main_query)
    rows = result.all()

    items = []
    for row in rows:
        prop = row[0]
        items.append(
            CidadaoProposicaoListItem(
                id=prop.id,
                tipo=prop.tipo,
                numero=prop.numero,
                ano=prop.ano,
                ementa=prop.ementa[:300] if prop.ementa else "",
                situacao=prop.situacao,
                temas=prop.temas,
                data_apresentacao=(
                    prop.data_apresentacao.isoformat()
                    if prop.data_apresentacao
                    else None
                ),
                resumo_ia=prop.resumo_ia,
                votos=_build_voto_resumo(
                    row.total_votos, row.votos_sim, row.votos_nao, row.votos_abstencao,
                ),
                tem_analise=bool(row.tem_analise),
                tem_comparativo=bool(row.tem_comparativo),
            )
        )

    return PaginatedProposicoes(
        total=total,
        items=items,
        pagina=pagina,
        itens_por_pagina=itens,
    )


@router.get("/proposicoes/{proposicao_id}", response_model=CidadaoProposicaoDetalhe)
@limiter.limit("60/minute")
async def obter_proposicao(
    request: Request,
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
) -> CidadaoProposicaoDetalhe:
    """Public proposição detail with AI analysis, votes, and comparativo."""

    result = await db.execute(
        select(Proposicao)
        .options(selectinload(Proposicao.analises))
        .where(Proposicao.id == proposicao_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Proposição não encontrada.")

    # ── Vote aggregation ──
    vote_result = await db.execute(
        select(
            func.count(VotoPopular.id).label("total"),
            func.sum(case((VotoPopular.voto == "SIM", 1), else_=0)).label("sim"),
            func.sum(case((VotoPopular.voto == "NAO", 1), else_=0)).label("nao"),
            func.sum(case((VotoPopular.voto == "ABSTENCAO", 1), else_=0)).label("abstencao"),
        ).where(VotoPopular.proposicao_id == proposicao_id)
    )
    vote_row = vote_result.one()
    votos = _build_voto_resumo(
        int(vote_row.total or 0),
        int(vote_row.sim or 0),
        int(vote_row.nao or 0),
        int(vote_row.abstencao or 0),
    )

    # ── Latest AI analysis ──
    analise: AnaliseIAPublica | None = None
    if prop.analises:
        latest = sorted(prop.analises, key=lambda a: a.versao, reverse=True)[0]
        analise = AnaliseIAPublica(
            resumo_leigo=latest.resumo_leigo,
            impacto_esperado=latest.impacto_esperado,
            areas_afetadas=latest.areas_afetadas or [],
            argumentos_favor=latest.argumentos_favor or [],
            argumentos_contra=latest.argumentos_contra or [],
        )

    # ── Latest comparativo ──
    comparativo: ComparativoPublico | None = None
    comp_result = await db.execute(
        select(ComparativoVotacao)
        .where(ComparativoVotacao.proposicao_id == proposicao_id)
        .order_by(desc(ComparativoVotacao.data_geracao))
        .limit(1)
    )
    comp = comp_result.scalar_one_or_none()
    if comp:
        comparativo = ComparativoPublico(
            resultado_camara=comp.resultado_camara,
            votos_camara_sim=comp.votos_camara_sim,
            votos_camara_nao=comp.votos_camara_nao,
            alinhamento=comp.alinhamento,
            resumo_ia=comp.resumo_ia,
        )

    return CidadaoProposicaoDetalhe(
        id=prop.id,
        tipo=prop.tipo,
        numero=prop.numero,
        ano=prop.ano,
        ementa=prop.ementa,
        situacao=prop.situacao,
        temas=prop.temas,
        data_apresentacao=(
            prop.data_apresentacao.isoformat() if prop.data_apresentacao else None
        ),
        resumo_ia=prop.resumo_ia,
        votos=votos,
        analise=analise,
        comparativo=comparativo,
    )


@router.get("/votos/por-tema", response_model=list[VotosPorTemaItem])
@limiter.limit("30/minute")
async def votos_por_tema(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[VotosPorTemaItem]:
    """Public vote breakdown by proposição tema."""
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

    tema_agg: dict[str, dict[str, int]] = {}
    for row in rows:
        temas = row.temas or []
        if isinstance(temas, str):
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

    items = [VotosPorTemaItem(tema=tema, **counts) for tema, counts in tema_agg.items()]
    items.sort(key=lambda x: x.total_votos, reverse=True)
    return items


@router.get("/votos/timeline", response_model=list[VotosTimelineItem])
@limiter.limit("30/minute")
async def votos_timeline(
    request: Request,
    dias: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[VotosTimelineItem]:
    """Public daily vote timeline."""
    cutoff = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ) - timedelta(days=dias)

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
    return [
        VotosTimelineItem(
            data=str(row.data) if row.data else "",
            total_votos=row.total_votos,
            sim=row.sim,
            nao=row.nao,
            abstencao=row.abstencao,
        )
        for row in result.all()
    ]


@router.get("/votos/ranking", response_model=list[VotosRankingItem])
@limiter.limit("30/minute")
async def votos_ranking(
    request: Request,
    limite: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[VotosRankingItem]:
    """Public ranking of most-voted proposições."""
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
        .group_by(
            Proposicao.id, Proposicao.tipo, Proposicao.numero,
            Proposicao.ano, Proposicao.ementa,
        )
        .order_by(desc("total_votos"))
        .limit(limite)
    )

    result = await db.execute(stmt)
    items: list[VotosRankingItem] = []
    for row in result.all():
        total = row.total_votos or 1
        items.append(
            VotosRankingItem(
                proposicao_id=row.proposicao_id,
                tipo=row.tipo,
                numero=row.numero,
                ano=row.ano,
                ementa=row.ementa[:200] if row.ementa else "",
                total_votos=row.total_votos,
                sim=row.sim,
                nao=row.nao,
                abstencao=row.abstencao,
                percentual_sim=round(row.sim / total * 100, 1),
                percentual_nao=round(row.nao / total * 100, 1),
            )
        )
    return items


@router.get("/comparativos", response_model=PaginatedComparativos)
@limiter.limit("30/minute")
async def listar_comparativos(
    request: Request,
    resultado: str | None = Query(None, description="APROVADO ou REJEITADO"),
    tema: str | None = Query(None, description="Filtrar por tema"),
    ordenar: str = Query("recentes", description="recentes | alinhamento_asc | alinhamento_desc"),
    pagina: int = Query(1, ge=1),
    itens: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedComparativos:
    """Public listing of popular-vs-parliamentary vote comparisons."""
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

    if resultado:
        base = base.where(ComparativoVotacao.resultado_camara == resultado.upper())

    if tema:
        # Tema filter post-query for cross-DB compat
        if ordenar == "alinhamento_asc":
            base = base.order_by(ComparativoVotacao.alinhamento.asc())
        elif ordenar == "alinhamento_desc":
            base = base.order_by(ComparativoVotacao.alinhamento.desc())
        else:
            base = base.order_by(ComparativoVotacao.data_geracao.desc())

        result = await db.execute(base)
        rows = result.all()

        tema_lower = tema.lower()
        filtered = [
            row for row in rows
            if (temas_parsed := _parse_temas(row.temas))
            and any(tema_lower in t.lower() for t in temas_parsed)
        ]

        total = len(filtered)
        start = (pagina - 1) * itens
        page_rows = filtered[start:start + itens]
    else:
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

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
        comp = row[0]
        items.append(
            ComparativoListItem(
                id=str(comp.id),
                proposicao_id=comp.proposicao_id,
                tipo=row.tipo,
                numero=row.numero,
                ano=row.ano,
                ementa=row.ementa[:200] if row.ementa else "",
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


@router.get("/comparativos/evolucao", response_model=list[EvolucaoAlinhamentoItem])
@limiter.limit("30/minute")
async def evolucao_alinhamento(
    request: Request,
    meses: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
) -> list[EvolucaoAlinhamentoItem]:
    """Public monthly alignment evolution."""
    stmt = (
        select(
            ComparativoVotacao.data_geracao,
            ComparativoVotacao.alinhamento,
        )
        .order_by(ComparativoVotacao.data_geracao)
    )

    result = await db.execute(stmt)
    rows = result.all()

    by_month: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.data_geracao is not None:
            mes = row.data_geracao.strftime("%Y-%m")
            by_month[mes].append(float(row.alinhamento or 0.5))

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
