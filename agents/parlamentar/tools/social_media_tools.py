"""FunctionTools for the SocialMediaAgent.

These tools are used by the SocialMediaAgent to generate text and
manage social media posts. The agent is invoked by Celery tasks,
NOT by direct user conversation.
"""

from __future__ import annotations


async def gerar_texto_post_social(
    tipo: str,
    rede: str,
    dados: str,
) -> dict:
    """Gera texto otimizado para uma rede social específica.

    Use esta ferramenta para criar o texto do post adaptado ao formato
    e limites de cada rede social.

    Args:
        tipo: Tipo do post — um de: resumo_semanal, votacao_relevante,
            comparativo, destaque_proposicao, explicativo_educativo.
        rede: Rede social destino — um de: twitter, facebook, instagram,
            linkedin, discord, reddit.
        dados: Dados estruturados em formato texto para o agente usar
            na composição. Inclui proposição, percentuais, resultados etc.

    Returns:
        Dict com status e o texto gerado para o post.
    """
    # This tool is a passthrough — the LLM generates the text directly
    # from the instruction + dados. The orchestrating code extracts the
    # content from the agent response.
    return {
        "status": "success",
        "message": (
            f"Gere o texto do post tipo '{tipo}' para a rede '{rede}' "
            f"usando os seguintes dados:\n\n{dados}"
        ),
    }


async def listar_posts_recentes(
    limite: int = 10,
) -> dict:
    """Lista posts sociais recentes publicados pelo sistema.

    Args:
        limite: Número máximo de posts a retornar (padrão 10).

    Returns:
        Dict com status e lista de posts recentes.
    """
    from app.tasks.helpers import get_async_session
    from app.repositories.social_post_repo import SocialPostRepository
    from app.domain.social_post import StatusPost

    try:
        async with get_async_session() as session:
            repo = SocialPostRepository(session)
            posts = await repo.find_recent_published(hours=168, limit=limite)
            items = [
                {
                    "id": str(p.id),
                    "tipo": p.tipo.value,
                    "rede": p.rede.value,
                    "status": p.status.value,
                    "texto": p.texto[:200],
                    "publicado_em": str(p.publicado_em) if p.publicado_em else None,
                    "likes": p.likes,
                    "shares": p.shares,
                }
                for p in posts
            ]
            return {"status": "success", "posts": items, "total": len(items)}
    except Exception:
        return {"status": "error", "error": "Não foi possível listar posts recentes."}


async def obter_metricas_posts() -> dict:
    """Obtém métricas agregadas de todos os posts publicados.

    Returns:
        Dict com métricas totais: posts, likes, shares, comments.
    """
    from app.tasks.helpers import get_async_session
    from app.repositories.social_post_repo import SocialPostRepository

    try:
        async with get_async_session() as session:
            repo = SocialPostRepository(session)
            metrics = await repo.get_aggregated_metrics()
            return {"status": "success", "metricas": metrics}
    except Exception:
        return {"status": "error", "error": "Não foi possível obter métricas."}
