"""FunctionTools for popular voting operations.

These tools handle voter registration of votes on propositions and
retrieval of voting results. Used by VotacaoAgent.

Votes are automatically classified as OFICIAL (eligible Brazilian citizen)
or OPINIAO (consultive) based on the voter's eligibility.
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

    O voto é automaticamente classificado:
    - OFICIAL: cidadão brasileiro, 16+ anos, verificado — conta no resultado
      oficial enviado aos parlamentares.
    - OPINIÃO: todos os demais — registrado como consultivo, não impacta o
      resultado oficial mas fica visível como opinião.

    Args:
        chat_id: ID do chat do eleitor no mensageiro.
        proposicao_id: ID da proposição legislativa.
        voto: Voto do eleitor: 'SIM', 'NAO' ou 'ABSTENCAO'.
        justificativa: Texto opcional explicando o motivo do voto.

    Returns:
        Dict com status da operação, tipo do voto e confirmação.
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

            if not eleitor.nome:
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

            tipo_voto = result.tipo_voto.value if hasattr(result.tipo_voto, 'value') else str(result.tipo_voto)
            is_oficial = tipo_voto == "OFICIAL"

            response = {
                "status": "success",
                "message": f"Voto {voto_upper} registrado com sucesso para a proposição {proposicao_id}!",
                "voto": {
                    "proposicao_id": proposicao_id,
                    "voto": voto_upper,
                    "tipo_voto": tipo_voto,
                    "data": str(result.data_voto),
                },
                "elegivel": is_oficial,
            }

            if not is_oficial:
                response["aviso_elegibilidade"] = (
                    "Seu voto foi registrado como OPINIÃO CONSULTIVA. "
                    "Para que seu voto conte no resultado oficial enviado aos parlamentares, "
                    "complete seu cadastro: informe que é cidadão brasileiro, "
                    "sua data de nascimento (16+ anos) e verifique sua conta."
                )

            return response
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def obter_resultado_votacao(proposicao_id: int) -> dict:
    """Obtém o resultado consolidado da votação popular sobre uma proposição.

    Retorna dois conjuntos de dados:
    - OFICIAL: votos de cidadãos brasileiros elegíveis (16+, verificados).
      Este é o resultado enviado aos parlamentares.
    - CONSULTIVO: todos os votos (oficiais + opiniões). Serve como
      termômetro geral de opinião.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e resultados oficial e consultivo da votação popular.
    """
    try:
        async with async_session_factory() as session:
            service = VotoPopularService(session)
            resultado_completo = await service.obter_resultado_completo(proposicao_id)

            oficial = resultado_completo["oficial"]
            consultivo = resultado_completo["consultivo"]

            return {
                "status": "success",
                "resultado_oficial": {
                    "proposicao_id": proposicao_id,
                    "descricao": "Votos de cidadãos brasileiros elegíveis (conta para parlamentares)",
                    "total_votos": oficial["total"],
                    "sim": oficial["SIM"],
                    "nao": oficial["NAO"],
                    "abstencao": oficial["ABSTENCAO"],
                    "percentual_sim": oficial["percentual_sim"],
                    "percentual_nao": oficial["percentual_nao"],
                    "percentual_abstencao": oficial["percentual_abstencao"],
                },
                "resultado_consultivo": {
                    "proposicao_id": proposicao_id,
                    "descricao": "Todos os votos (oficiais + opiniões consultivas)",
                    "total_votos": consultivo["total"],
                    "sim": consultivo["SIM"],
                    "nao": consultivo["NAO"],
                    "abstencao": consultivo["ABSTENCAO"],
                    "percentual_sim": consultivo["percentual_sim"],
                    "percentual_nao": consultivo["percentual_nao"],
                    "percentual_abstencao": consultivo["percentual_abstencao"],
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
