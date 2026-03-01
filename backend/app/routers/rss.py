"""RSS Feed endpoints — public feeds for voter results and comparatives."""

from datetime import datetime, timezone
from typing import Sequence

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.domain.proposicao import Proposicao
from app.domain.comparativo import ComparativoVotacao
from app.services.publicacao_service import PublicacaoService
from app.services.voto_popular_service import VotoPopularService
from app.logging import get_logger

router = APIRouter(prefix="/rss", tags=["rss"])

logger = get_logger(__name__)


def _build_rss_header(title: str, description: str, link: str) -> str:
    """Build RSS 2.0 XML header."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <language>pt-br</language>
  <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
  <ttl>15</ttl>
"""


def _build_rss_footer() -> str:
    """Build RSS 2.0 XML footer."""
    return """</channel>
</rss>"""


def _build_vote_item(proposicao: Proposicao, resultado: dict) -> str:
    """Build an RSS item for a vote result."""
    total = resultado.get("total", 0)
    sim = resultado.get("SIM", 0)
    nao = resultado.get("NAO", 0)
    abstencao = resultado.get("ABSTENCAO", 0)
    p_sim = resultado.get("percentual_sim", 0.0)
    p_nao = resultado.get("percentual_nao", 0.0)

    temas = proposicao.temas or []
    categories = "\n    ".join(f"<category>{t}</category>" for t in temas)

    return f"""  <item>
    <title>{proposicao.tipo} {proposicao.numero}/{proposicao.ano} - Voto Popular</title>
    <description>{p_sim:.0f}% dos eleitores votaram SIM ({sim} votos). {p_nao:.0f}% votaram NÃO. Total: {total} votos.</description>
    <link>https://parlamentaria.app/proposicao/{proposicao.id}</link>
    <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
    {categories}
  </item>
"""


def _build_comparativo_item(comparativo: ComparativoVotacao) -> str:
    """Build an RSS item for a comparative analysis."""
    alinhamento_pct = comparativo.alinhamento * 100

    return f"""  <item>
    <title>Comparativo Proposição {comparativo.proposicao_id} - Alinhamento {alinhamento_pct:.0f}%</title>
    <description>Resultado Câmara: {comparativo.resultado_camara}. Voto Popular: {comparativo.voto_popular_sim} SIM, {comparativo.voto_popular_nao} NÃO. Alinhamento: {alinhamento_pct:.1f}%.</description>
    <link>https://parlamentaria.app/proposicao/{comparativo.proposicao_id}</link>
    <pubDate>{comparativo.data_geracao.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
  </item>
"""


@router.get("/votos", response_class=Response)
async def rss_votos(
    token: str = Query(..., description="RSS subscription token"),
    tema: str | None = Query(None, description="Filter by theme"),
    uf: str | None = Query(None, description="Filter by UF"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """RSS Feed with consolidated popular vote results.

    Requires a valid RSS subscription token.
    """
    publicacao_service = PublicacaoService(db)
    voto_service = VotoPopularService(db)

    # Validate token
    assinatura = await publicacao_service.get_rss_by_token(token)
    if not assinatura:
        return Response(
            content="<error>Token inválido ou assinatura inativa</error>",
            media_type="application/xml",
            status_code=403,
        )

    # Update last access
    assinatura.ultimo_acesso = datetime.now(timezone.utc)
    await db.flush()

    # Build feed
    xml = _build_rss_header(
        title="Parlamentaria — Votos Populares",
        description="Resultados consolidados de votação popular sobre proposições legislativas",
        link="https://parlamentaria.app/rss/votos",
    )

    # Fetch propositions with popular votes
    from sqlalchemy import select, distinct
    stmt = select(distinct(VotoPopular.proposicao_id))
    result = await db.execute(stmt)
    proposicao_ids = [row[0] for row in result.all()]

    from app.services.proposicao_service import ProposicaoService
    prop_service = ProposicaoService(db)

    # Build effective theme filter: query param > subscription config
    active_temas: list[str] = []
    if tema:
        active_temas = [tema.lower()]
    elif assinatura.filtro_temas:
        active_temas = [t.lower() for t in assinatura.filtro_temas]

    for prop_id in proposicao_ids[:50]:  # Limit feed to 50 latest
        try:
            proposicao = await prop_service.get_by_id(prop_id)
        except Exception:
            continue

        # Apply theme filter
        if active_temas and proposicao.temas:
            prop_temas_lower = [t.lower() for t in proposicao.temas]
            if not any(t in prop_temas_lower for t in active_temas):
                continue

        resultado = await voto_service.obter_resultado(prop_id)
        if resultado and resultado["total"] > 0:
            xml += _build_vote_item(proposicao, resultado)

    xml += _build_rss_footer()

    logger.info("rss.votos.served", token=token[:8])
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@router.get("/comparativos", response_class=Response)
async def rss_comparativos(
    token: str = Query(..., description="RSS subscription token"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """RSS Feed with popular vs parliamentary vote comparatives."""
    publicacao_service = PublicacaoService(db)

    # Validate token
    assinatura = await publicacao_service.get_rss_by_token(token)
    if not assinatura:
        return Response(
            content="<error>Token inválido ou assinatura inativa</error>",
            media_type="application/xml",
            status_code=403,
        )

    assinatura.ultimo_acesso = datetime.now(timezone.utc)
    await db.flush()

    xml = _build_rss_header(
        title="Parlamentaria — Comparativos Pop vs Real",
        description="Comparativos entre voto popular e votação real na Câmara dos Deputados",
        link="https://parlamentaria.app/rss/comparativos",
    )

    # Fetch comparatives
    from sqlalchemy import select
    stmt = select(ComparativoVotacao).order_by(ComparativoVotacao.data_geracao.desc()).limit(50)
    result = await db.execute(stmt)
    comparativos = result.scalars().all()

    for comp in comparativos:
        xml += _build_comparativo_item(comp)

    xml += _build_rss_footer()

    logger.info("rss.comparativos.served", token=token[:8])
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")
