"""FunctionTools for publication and comparative analysis.

These tools handle comparison between popular and parliamentary votes,
and provide information about RSS feed status. Used by PublicacaoAgent.
"""

from __future__ import annotations

from app.db.session import async_session_factory
from app.services.comparativo_service import ComparativoService


async def obter_comparativo(proposicao_id: int) -> dict:
    """Obtém o comparativo entre o voto popular e o resultado parlamentar.

    Mostra como os eleitores votaram versus como os deputados votaram,
    com um índice de alinhamento de 0 a 100%.

    Args:
        proposicao_id: ID da proposição que teve votação.

    Returns:
        Dict com status e dados do comparativo incluindo alinhamento.
    """
    try:
        async with async_session_factory() as session:
            service = ComparativoService(session)
            comparativo = await service.get_by_proposicao(proposicao_id)

            if comparativo is None:
                return {
                    "status": "not_found",
                    "message": (
                        f"Nenhum comparativo disponível para a proposição {proposicao_id}. "
                        "O comparativo é gerado quando a Câmara vota uma proposição "
                        "que também teve votação popular."
                    ),
                }

            alinhamento_pct = round(comparativo.alinhamento * 100, 1)

            return {
                "status": "success",
                "comparativo": {
                    "proposicao_id": comparativo.proposicao_id,
                    "voto_popular": {
                        "sim": comparativo.voto_popular_sim,
                        "nao": comparativo.voto_popular_nao,
                        "abstencao": comparativo.voto_popular_abstencao,
                    },
                    "resultado_camara": comparativo.resultado_camara,
                    "votos_camara": {
                        "sim": comparativo.votos_camara_sim,
                        "nao": comparativo.votos_camara_nao,
                    },
                    "alinhamento": alinhamento_pct,
                    "resumo_ia": comparativo.resumo_ia or "",
                    "data_geracao": str(comparativo.data_geracao),
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def status_publicacao() -> dict:
    """Informa sobre o sistema de publicação de votos populares.

    Explica como parlamentares e sistemas externos podem acompanhar
    os resultados das votações populares via RSS ou Webhooks.

    Returns:
        Dict com informações sobre os canais de publicação disponíveis.
    """
    from app.config import settings

    return {
        "status": "success",
        "publicacao": {
            "rss_feed": {
                "url_votos": f"{settings.rss_base_url}/votos",
                "url_comparativos": f"{settings.rss_base_url}/comparativos",
                "descricao": (
                    "Feed RSS 2.0 com resultados consolidados de votação popular. "
                    "Parlamentares podem assinar para acompanhar como os eleitores "
                    "estão votando nas proposições."
                ),
            },
            "webhooks": {
                "eventos": ["voto_consolidado", "comparativo_gerado", "nova_proposicao"],
                "descricao": (
                    "Sistemas externos podem registrar webhooks para receber "
                    "notificações em tempo real sobre votos populares."
                ),
            },
        },
    }
