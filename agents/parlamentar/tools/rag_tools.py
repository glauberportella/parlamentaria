"""FunctionTools for RAG (Retrieval-Augmented Generation) semantic search.

These tools give agents the ability to search propositions and legislative
texts using natural language — powered by pgvector semantic similarity.
"""

from __future__ import annotations

from app.db.session import async_session_factory
from app.services.rag_service import RAGService


async def busca_semantica_proposicoes(
    consulta: str,
    limite: int = 5,
) -> dict:
    """Busca proposições legislativas por similaridade semântica.

    Use esta ferramenta quando o eleitor fizer perguntas em linguagem natural
    sobre proposições, como "projetos sobre reforma tributária" ou
    "o que está sendo discutido sobre educação?". Esta ferramenta encontra
    proposições relevantes mesmo sem palavras-chave exatas.

    PREFIRA esta ferramenta em vez de buscar_proposicoes quando a pergunta
    for genérica ou em linguagem natural.

    Args:
        consulta: Pergunta ou tema em linguagem natural do eleitor.
            Ex: "reforma da previdência", "projetos sobre saúde pública",
            "o que mudou na legislação ambiental?".
        limite: Número máximo de proposições a retornar (padrão 5).

    Returns:
        Dict com status e lista de proposições relevantes ordenadas por
        relevância, incluindo conteúdo do trecho mais similar.
    """
    try:
        async with async_session_factory() as session:
            rag_service = RAGService(session)
            results = await rag_service.search_proposicoes(
                query=consulta,
                limit=min(limite, 10),
            )

            if not results:
                return {
                    "status": "success",
                    "message": "Nenhuma proposição relevante encontrada para esta consulta.",
                    "proposicoes": [],
                    "total": 0,
                    "sugestao": "Tente reformular a pergunta com outros termos ou use buscar_proposicoes com filtros exatos.",
                }

            proposicoes = []
            for r in results:
                metadata = r.get("metadata", {})
                proposicoes.append({
                    "proposicao_id": r["proposicao_id"],
                    "tipo": metadata.get("tipo", ""),
                    "numero": metadata.get("numero", ""),
                    "ano": metadata.get("ano", ""),
                    "temas": metadata.get("temas", []),
                    "trecho_relevante": r["content"],
                    "relevancia": f"{r['similarity']:.0%}",
                    "tipo_conteudo": r["chunk_type"],
                })

            return {
                "status": "success",
                "proposicoes": proposicoes,
                "total": len(proposicoes),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": "A busca semântica não está disponível no momento. Use buscar_proposicoes como alternativa.",
        }


async def obter_estatisticas_rag() -> dict:
    """Obtém estatísticas do índice de busca semântica.

    Use para informar ao eleitor quantas proposições estão disponíveis
    para busca semântica e diagnóstico do sistema.

    Returns:
        Dict com total de chunks indexados, por tipo e proposições únicas.
    """
    try:
        async with async_session_factory() as session:
            rag_service = RAGService(session)
            stats = await rag_service.get_index_stats()
            return {
                "status": "success",
                "estatisticas": {
                    "total_trechos_indexados": stats["total_chunks"],
                    "por_tipo": stats["by_type"],
                    "proposicoes_indexadas": stats["unique_proposicoes"],
                },
            }
    except Exception as e:
        return {
            "status": "error",
            "error": "Não foi possível obter as estatísticas do índice de busca no momento.",
        }
