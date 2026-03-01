"""FunctionTools for popular voting operations.

These tools handle voter registration of votes on propositions and
retrieval of voting results. Used by VotacaoAgent.
"""

from __future__ import annotations

import uuid

from app.db.session import async_session_factory
from app.domain.voto_popular import VotoEnum
from app.services.voto_popular_service import VotoPopularService
from app.services.eleitor_service import EleitorService


async def registrar_voto(
    chat_id: str,
    proposicao_id: int,
    voto: str,
    justificativa: str = "",
) -> dict:
    """Registra o voto popular de um eleitor sobre uma proposição.

    O eleitor pode votar SIM, NAO ou ABSTENCAO. Cada eleitor pode votar
    apenas uma vez por proposição — se votar novamente, o último voto
    substitui o anterior.

    Args:
        chat_id: ID do chat do eleitor no mensageiro.
        proposicao_id: ID da proposição legislativa.
        voto: Voto do eleitor: 'SIM', 'NAO' ou 'ABSTENCAO'.
        justificativa: Texto opcional explicando o motivo do voto.

    Returns:
        Dict com status da operação e confirmação do voto registrado.
    """
    try:
        # Validate voto
        voto_upper = voto.upper().strip()
        voto_map = {"SIM": VotoEnum.SIM, "NAO": VotoEnum.NAO, "ABSTENCAO": VotoEnum.ABSTENCAO}
        if voto_upper not in voto_map:
            return {
                "status": "error",
                "error": "Voto inválido. Use SIM, NAO ou ABSTENCAO.",
            }

        async with async_session_factory() as session:
            eleitor_service = EleitorService(session)
            eleitor = await eleitor_service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "error",
                    "error": "Você precisa se cadastrar antes de votar. Me diga seu nome e estado.",
                }

            if not eleitor.verificado and not eleitor.nome:
                return {
                    "status": "error",
                    "error": "Complete seu cadastro (nome e UF) antes de votar.",
                }

            voto_service = VotoPopularService(session)
            result = await voto_service.registrar_voto(
                eleitor_id=eleitor.id,
                proposicao_id=proposicao_id,
                voto=voto_map[voto_upper],
                justificativa=justificativa if justificativa else None,
            )
            await session.commit()

            return {
                "status": "success",
                "message": f"Voto {voto_upper} registrado com sucesso para a proposição {proposicao_id}!",
                "voto": {
                    "proposicao_id": proposicao_id,
                    "voto": voto_upper,
                    "data": str(result.data_voto),
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_resultado_votacao(proposicao_id: int) -> dict:
    """Obtém o resultado consolidado da votação popular sobre uma proposição.

    Mostra quantos eleitores votaram SIM, NÃO e ABSTENÇÃO, com percentuais.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e resultado consolidado da votação popular.
    """
    try:
        async with async_session_factory() as session:
            service = VotoPopularService(session)
            resultado = await service.obter_resultado(proposicao_id)

            return {
                "status": "success",
                "resultado": {
                    "proposicao_id": proposicao_id,
                    "total_votos": resultado["total"],
                    "sim": resultado["SIM"],
                    "nao": resultado["NAO"],
                    "abstencao": resultado["ABSTENCAO"],
                    "percentual_sim": resultado["percentual_sim"],
                    "percentual_nao": resultado["percentual_nao"],
                    "percentual_abstencao": resultado["percentual_abstencao"],
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def consultar_meu_voto(
    chat_id: str,
    proposicao_id: int,
) -> dict:
    """Verifica como o eleitor votou em uma proposição específica.

    Args:
        chat_id: ID do chat do eleitor.
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e o voto do eleitor, ou mensagem se não votou.
    """
    try:
        async with async_session_factory() as session:
            eleitor_service = EleitorService(session)
            eleitor = await eleitor_service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado.",
                }

            voto_service = VotoPopularService(session)
            voto = await voto_service.get_voto(eleitor.id, proposicao_id)

            if voto is None:
                return {
                    "status": "not_found",
                    "message": f"Você ainda não votou na proposição {proposicao_id}.",
                }

            return {
                "status": "success",
                "voto": {
                    "proposicao_id": proposicao_id,
                    "voto": voto.voto.value if hasattr(voto.voto, 'value') else str(voto.voto),
                    "data": str(voto.data_voto),
                    "justificativa": voto.justificativa or "",
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def historico_votos_eleitor(
    chat_id: str,
    limite: int = 10,
) -> dict:
    """Lista o histórico de votos populares de um eleitor.

    Mostra todas as proposições em que o eleitor votou.

    Args:
        chat_id: ID do chat do eleitor.
        limite: Máximo de votos a retornar (padrão 10).

    Returns:
        Dict com status e lista de votos do eleitor.
    """
    try:
        async with async_session_factory() as session:
            eleitor_service = EleitorService(session)
            eleitor = await eleitor_service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado.",
                }

            voto_service = VotoPopularService(session)
            votos = await voto_service.list_by_eleitor(
                eleitor.id, limit=min(limite, 50)
            )

            items = []
            for v in votos:
                items.append({
                    "proposicao_id": v.proposicao_id,
                    "voto": v.voto.value if hasattr(v.voto, 'value') else str(v.voto),
                    "data": str(v.data_voto),
                })

            return {
                "status": "success",
                "votos": items,
                "total": len(items),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
