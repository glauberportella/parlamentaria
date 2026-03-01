"""FunctionTools for publication and comparative analysis.

These tools handle comparison between popular and parliamentary votes,
and provide information about RSS feed status. Used by PublicacaoAgent.
"""

from __future__ import annotations


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
        from app.db.session import async_session_factory
        from app.services.comparativo_service import ComparativoService

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


async def consultar_assinaturas_ativas() -> dict:
    """Consulta o número de assinaturas ativas de RSS e Webhooks.

    Informa quantos parlamentares e sistemas externos estão acompanhando
    os resultados das votações populares em tempo real.

    Returns:
        Dict com contagens de assinaturas RSS e Webhooks ativas.
    """
    try:
        from app.db.session import async_session_factory
        from app.services.publicacao_service import PublicacaoService

        async with async_session_factory() as session:
            service = PublicacaoService(session)
            rss_subs = await service.list_rss_subscriptions(active_only=True)
            webhooks = await service.list_webhooks_for_event("voto_consolidado")
            webhooks_comp = await service.list_webhooks_for_event("comparativo_gerado")

            return {
                "status": "success",
                "assinaturas": {
                    "rss_ativas": len(rss_subs),
                    "webhooks_voto_consolidado": len(webhooks),
                    "webhooks_comparativo_gerado": len(webhooks_comp),
                    "descricao": (
                        f"{len(rss_subs)} parlamentares/organizações acompanham via RSS. "
                        f"{len(webhooks)} sistemas recebem notificações de votos. "
                        f"{len(webhooks_comp)} sistemas recebem comparativos."
                    ),
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def disparar_evento_publicacao(
    evento: str,
    proposicao_id: int,
) -> dict:
    """Dispara um evento de publicação para todos os webhooks assinados.

    Usado para notificar sistemas externos sobre novos votos populares
    consolidados ou comparativos gerados.

    Args:
        evento: Tipo do evento ('voto_consolidado', 'comparativo_gerado', 'nova_proposicao').
        proposicao_id: ID da proposição relacionada ao evento.

    Returns:
        Dict com status do dispatch e contagem de webhooks notificados.
    """
    valid_events = ["voto_consolidado", "comparativo_gerado", "nova_proposicao"]
    if evento not in valid_events:
        return {
            "status": "error",
            "message": f"Evento inválido. Eventos válidos: {', '.join(valid_events)}",
        }

    try:
        from app.db.session import async_session_factory
        from app.services.publicacao_service import PublicacaoService

        async with async_session_factory() as session:
            service = PublicacaoService(session)
            payload = {
                "proposicao_id": proposicao_id,
            }
            stats = await service.dispatch_event(evento, payload)
            await session.commit()

            return {
                "status": "success",
                "dispatch": {
                    "evento": evento,
                    "total_webhooks": stats["total"],
                    "sucesso": stats["success"],
                    "falhas": stats["failed"],
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
