"""Proposições endpoints for the parlamentar dashboard.

Provides enriched listing with filters, pagination, and detail view
including AI analysis, popular vote results, and comparativo data.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.domain.analise_ia import AnaliseIA
from app.domain.comparativo import ComparativoVotacao
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.logging import get_logger
from app.routers.parlamentar.auth import get_current_parlamentar_user
from app.schemas.parlamentar import ParlamentarUserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/proposicoes", tags=["parlamentar-proposicoes"])


# ──────────────────────────────────────────────
#  Response schemas
# ──────────────────────────────────────────────


class VotoPopularResumo(BaseModel):
    """Resumo de votos populares de uma proposição."""

    total: int = 0
    sim: int = 0
    nao: int = 0
    abstencao: int = 0
    percentual_sim: float = 0.0
    percentual_nao: float = 0.0
    percentual_abstencao: float = 0.0


class AnaliseIAResumo(BaseModel):
    """Resumo da análise IA de uma proposição."""

    id: str
    resumo_leigo: str
    impacto_esperado: str
    areas_afetadas: list[str]
    argumentos_favor: list[str]
    argumentos_contra: list[str]
    data_geracao: datetime
    versao: int


class ComparativoResumo(BaseModel):
    """Resumo do comparativo pop vs real."""

    id: str
    resultado_camara: str
    votos_camara_sim: int
    votos_camara_nao: int
    alinhamento: float
    resumo_ia: str | None = None
    data_geracao: datetime


class ProposicaoListItem(BaseModel):
    """Proposição item for listing with enriched data."""

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


class ProposicaoDetalhe(BaseModel):
    """Full proposição detail with all enriched data."""

    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    texto_completo_url: str | None = None
    situacao: str | None = None
    temas: list[str] | None = None
    autores: list[dict] | None = None
    data_apresentacao: str | None = None
    resumo_ia: str | None = None
    ultima_sincronizacao: str | None = None
    votos: VotoPopularResumo
    analise: AnaliseIAResumo | None = None
    comparativo: ComparativoResumo | None = None


class PaginatedProposicoes(BaseModel):
    """Paginated proposições response."""

    total: int
    items: list[ProposicaoListItem]
    pagina: int
    itens_por_pagina: int


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────


def _build_voto_resumo(
    total: int, sim: int, nao: int, abstencao: int
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


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────


@router.get("", response_model=PaginatedProposicoes)
async def listar_proposicoes(
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
    db: AsyncSession = Depends(get_db),
    tema: str | None = Query(None, description="Filtrar por tema"),
    tipo: str | None = Query(None, description="Filtrar por tipo (PL, PEC, MPV...)"),
    ano: int | None = Query(None, description="Filtrar por ano"),
    situacao: str | None = Query(None, description="Filtrar por situação"),
    busca: str | None = Query(None, description="Busca por texto na ementa"),
    ordenar: str = Query(
        "recentes",
        description="Ordenação: recentes, votos_desc, votos_asc, ano_desc",
    ),
    pagina: int = Query(1, ge=1, description="Número da página"),
    itens: int = Query(20, ge=1, le=100, description="Itens por página"),
) -> PaginatedProposicoes:
    """List proposições with filters, pagination, and enriched vote data."""

    # ── Base query with vote aggregation ──
    vote_subq = (
        select(
            VotoPopular.proposicao_id,
            func.count(VotoPopular.id).label("total_votos"),
            func.sum(case((VotoPopular.voto == "SIM", 1), else_=0)).label("votos_sim"),
            func.sum(case((VotoPopular.voto == "NAO", 1), else_=0)).label("votos_nao"),
            func.sum(case((VotoPopular.voto == "ABSTENCAO", 1), else_=0)).label(
                "votos_abstencao"
            ),
        )
        .group_by(VotoPopular.proposicao_id)
        .subquery()
    )

    # Check for analise existence (count is SQLite-compatible, unlike bool_or)
    analise_subq = (
        select(
            AnaliseIA.proposicao_id,
            func.count(AnaliseIA.id).label("tem_analise"),
        )
        .group_by(AnaliseIA.proposicao_id)
        .subquery()
    )

    # Check for comparativo existence
    comparativo_subq = (
        select(
            ComparativoVotacao.proposicao_id,
            func.count(ComparativoVotacao.id).label("tem_comparativo"),
        )
        .group_by(ComparativoVotacao.proposicao_id)
        .subquery()
    )

    # ── Apply filters ──
    base_filter = select(Proposicao)

    if tema:
        base_filter = base_filter.where(Proposicao.temas.any(tema))
    if tipo:
        base_filter = base_filter.where(Proposicao.tipo == tipo.upper())
    if ano:
        base_filter = base_filter.where(Proposicao.ano == ano)
    if situacao:
        base_filter = base_filter.where(Proposicao.situacao.ilike(f"%{situacao}%"))
    if busca:
        base_filter = base_filter.where(Proposicao.ementa.ilike(f"%{busca}%"))

    # ── Count total ──
    count_query = select(func.count()).select_from(base_filter.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # ── Main query with joins ──
    main_query = (
        base_filter.outerjoin(vote_subq, vote_subq.c.proposicao_id == Proposicao.id)
        .outerjoin(analise_subq, analise_subq.c.proposicao_id == Proposicao.id)
        .outerjoin(
            comparativo_subq, comparativo_subq.c.proposicao_id == Proposicao.id
        )
        .add_columns(
            func.coalesce(vote_subq.c.total_votos, 0).label("total_votos"),
            func.coalesce(vote_subq.c.votos_sim, 0).label("votos_sim"),
            func.coalesce(vote_subq.c.votos_nao, 0).label("votos_nao"),
            func.coalesce(vote_subq.c.votos_abstencao, 0).label("votos_abstencao"),
            func.coalesce(analise_subq.c.tem_analise, 0).label("tem_analise"),
            func.coalesce(comparativo_subq.c.tem_comparativo, 0).label(
                "tem_comparativo"
            ),
        )
    )

    # ── Ordering ──
    if ordenar == "votos_desc":
        main_query = main_query.order_by(desc("total_votos"), desc(Proposicao.id))
    elif ordenar == "votos_asc":
        main_query = main_query.order_by(asc("total_votos"), desc(Proposicao.id))
    elif ordenar == "ano_desc":
        main_query = main_query.order_by(
            desc(Proposicao.ano), desc(Proposicao.numero)
        )
    else:  # recentes (default)
        main_query = main_query.order_by(desc(Proposicao.id))

    # ── Pagination ──
    offset = (pagina - 1) * itens
    main_query = main_query.offset(offset).limit(itens)

    result = await db.execute(main_query)
    rows = result.all()

    items = []
    for row in rows:
        prop = row[0]  # Proposicao entity
        total_votos = row.total_votos
        votos_sim = row.votos_sim
        votos_nao = row.votos_nao
        votos_abstencao = row.votos_abstencao

        items.append(
            ProposicaoListItem(
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
                    total_votos, votos_sim, votos_nao, votos_abstencao
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


@router.get("/{proposicao_id}", response_model=ProposicaoDetalhe)
async def obter_proposicao(
    proposicao_id: int,
    current_user: ParlamentarUserResponse = Depends(get_current_parlamentar_user),
    db: AsyncSession = Depends(get_db),
) -> ProposicaoDetalhe:
    """Get full proposição detail with AI analysis, votes, and comparativo."""
    from fastapi import HTTPException

    # Load proposição with relationships
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
            func.sum(case((VotoPopular.voto == "ABSTENCAO", 1), else_=0)).label(
                "abstencao"
            ),
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
    analise: AnaliseIAResumo | None = None
    if prop.analises:
        latest = sorted(prop.analises, key=lambda a: a.versao, reverse=True)[0]
        analise = AnaliseIAResumo(
            id=str(latest.id),
            resumo_leigo=latest.resumo_leigo,
            impacto_esperado=latest.impacto_esperado,
            areas_afetadas=latest.areas_afetadas or [],
            argumentos_favor=latest.argumentos_favor or [],
            argumentos_contra=latest.argumentos_contra or [],
            data_geracao=latest.data_geracao,
            versao=latest.versao,
        )

    # ── Latest comparativo ──
    comparativo: ComparativoResumo | None = None
    comp_result = await db.execute(
        select(ComparativoVotacao)
        .where(ComparativoVotacao.proposicao_id == proposicao_id)
        .order_by(desc(ComparativoVotacao.data_geracao))
        .limit(1)
    )
    comp = comp_result.scalar_one_or_none()
    if comp:
        comparativo = ComparativoResumo(
            id=str(comp.id),
            resultado_camara=comp.resultado_camara,
            votos_camara_sim=comp.votos_camara_sim,
            votos_camara_nao=comp.votos_camara_nao,
            alinhamento=comp.alinhamento,
            resumo_ia=comp.resumo_ia,
            data_geracao=comp.data_geracao,
        )

    # ── Build autores list ──
    autores_list: list[dict] | None = None
    if prop.autores:
        if isinstance(prop.autores, list):
            autores_list = prop.autores
        elif isinstance(prop.autores, dict):
            autores_list = [prop.autores]

    return ProposicaoDetalhe(
        id=prop.id,
        tipo=prop.tipo,
        numero=prop.numero,
        ano=prop.ano,
        ementa=prop.ementa,
        texto_completo_url=prop.texto_completo_url,
        situacao=prop.situacao,
        temas=prop.temas,
        autores=autores_list,
        data_apresentacao=(
            prop.data_apresentacao.isoformat() if prop.data_apresentacao else None
        ),
        resumo_ia=prop.resumo_ia,
        ultima_sincronizacao=(
            prop.ultima_sincronizacao.isoformat()
            if prop.ultima_sincronizacao
            else None
        ),
        votos=votos,
        analise=analise,
        comparativo=comparativo,
    )
