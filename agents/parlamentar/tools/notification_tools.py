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
            return {
                "status": "success",
                "notificacoes": {
                    "ativas": len(temas) > 0,
                    "temas": temas,
                    "mensagem": (
                        f"Você receberá notificações sobre: {', '.join(temas)}"
                        if temas
                        else "Nenhum tema configurado. Informe seus temas de interesse."
                    ),
                },
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}
