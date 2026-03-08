"""FunctionTools for proactive notification management.

Tools to manage voter notification preferences and status.
Used by EleitorAgent.
"""

from __future__ import annotations


async def verificar_notificacoes(chat_id: str) -> dict:
    """Verifica o status das notificações proativas de um eleitor.

    Informa se as notificações estão ativas e quais temas estão configurados.

    Args:
        chat_id: ID do chat do eleitor no mensageiro.

    Returns:
        Dict com status das notificações e temas configurados.
    """
    try:
        from app.db.session import async_session_factory
        from app.services.eleitor_service import EleitorService

        async with async_session_factory() as session:
            service = EleitorService(session)
            eleitor = await service.get_by_chat_id(chat_id)

            if eleitor is None:
                return {
                    "status": "not_found",
                    "message": "Eleitor não cadastrado. Faça o cadastro para receber notificações.",
                }

            temas = eleitor.temas_interesse or []
            freq_labels = {
                "IMEDIATA": "imediata (alertas em tempo real + resumo diário)",
                "DIARIA": "diária (resumo todo dia)",
                "SEMANAL": "semanal (resumo toda segunda-feira)",
                "DESATIVADA": "desativada",
            }
            freq = eleitor.frequencia_notificacao.value
            horario = eleitor.horario_preferido_notificacao

            return {
                "status": "success",
                "notificacoes": {
                    "ativas": freq != "DESATIVADA",
                    "temas": temas,
                    "frequencia": freq,
                    "frequencia_descricao": freq_labels.get(freq, freq),
                    "horario_preferido": horario,
                    "mensagem": (
                        f"Frequência: {freq_labels.get(freq, freq)}. "
                        f"Horário preferido: {horario}h. "
                        + (
                            f"Temas: {', '.join(temas)}."
                            if temas
                            else "Nenhum tema configurado."
                        )
                    ),
                },
            }
    except Exception:
        return {
            "status": "error",
            "error": "Não foi possível verificar as notificações no momento.",
        }


async def configurar_frequencia_notificacao(
    chat_id: str,
    frequencia: str,
    horario: int = 9,
) -> dict:
    """Configura a frequência de notificações do eleitor.

    Permite que o eleitor escolha com que frequência deseja receber
    o Resumo da Câmara (digest) com novidades legislativas.

    Args:
        chat_id: ID do chat do eleitor no mensageiro.
        frequencia: Frequência desejada. Valores aceitos:
            'IMEDIATA' — alertas em tempo real + resumo diário.
            'DIARIA' — resumo diário às 8h30.
            'SEMANAL' — resumo toda segunda-feira às 9h (padrão).
            'DESATIVADA' — sem notificações periódicas.
        horario: Hora preferida para receber o resumo (0 a 23, padrão 9).

    Returns:
        Dict com status e mensagem de confirmação.
    """
    try:
        from app.db.session import async_session_factory
        from app.domain.eleitor import FrequenciaNotificacao
        from app.services.digest_service import DigestService

        # Validate frequency
        freq_map = {
            "IMEDIATA": FrequenciaNotificacao.IMEDIATA,
            "DIARIA": FrequenciaNotificacao.DIARIA,
            "SEMANAL": FrequenciaNotificacao.SEMANAL,
            "DESATIVADA": FrequenciaNotificacao.DESATIVADA,
        }
        freq_upper = frequencia.upper().strip()
        if freq_upper not in freq_map:
            return {
                "status": "error",
                "error": (
                    "Frequência inválida. Opções: "
                    "IMEDIATA, DIARIA, SEMANAL ou DESATIVADA."
                ),
            }

        async with async_session_factory() as session:
            service = DigestService(session)
            result = await service.update_notification_preferences(
                chat_id=chat_id,
                frequencia=freq_map[freq_upper],
                horario=horario,
            )
            return result

    except Exception:
        return {
            "status": "error",
            "error": "Não foi possível atualizar suas preferências de notificação.",
        }


async def enviar_resultado_votacao(
    proposicao_id: int,
) -> dict:
    """Consulta e retorna o resultado consolidado da votação popular.

    Mostra o resultado detalhado com percentuais e total de votos
    para informar tanto o eleitor quanto para publicação.

    Args:
        proposicao_id: ID da proposição.

    Returns:
        Dict com status e resultado consolidado formatado.
    """
    try:
        from app.db.session import async_session_factory
        from app.services.voto_popular_service import VotoPopularService

        async with async_session_factory() as session:
            service = VotoPopularService(session)
            resultado = await service.obter_resultado(proposicao_id)

            total = resultado["total"]
            if total == 0:
                return {
                    "status": "success",
                    "message": f"Nenhum voto popular registrado para a proposição {proposicao_id}.",
                    "resultado": resultado,
                }

            # Determine majority
            if resultado["SIM"] > resultado["NAO"]:
                maioria = "SIM"
                maioria_pct = resultado["percentual_sim"]
            elif resultado["NAO"] > resultado["SIM"]:
                maioria = "NÃO"
                maioria_pct = resultado["percentual_nao"]
            else:
                maioria = "EMPATE"
                maioria_pct = 50.0

            message = (
                f"Resultado da votação popular para a proposição {proposicao_id}:\n\n"
                f"✅ SIM: {resultado['SIM']} votos ({resultado['percentual_sim']:.1f}%)\n"
                f"❌ NÃO: {resultado['NAO']} votos ({resultado['percentual_nao']:.1f}%)\n"
                f"⚪ Abstenção: {resultado['ABSTENCAO']} votos ({resultado['percentual_abstencao']:.1f}%)\n"
                f"📊 Total: {total} votos\n\n"
                f"{'Maioria: ' + maioria + ' (' + f'{maioria_pct:.1f}%' + ')' if maioria != 'EMPATE' else 'Resultado: EMPATE'}"
            )

            return {
                "status": "success",
                "message": message,
                "resultado": resultado,
                "maioria": maioria,
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
