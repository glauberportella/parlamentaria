"""Telegram command and message handlers.

Processes commands (/start, /ajuda, /proposicoes, etc.) and routes regular
messages to the ADK agent. Also handles callback queries from inline keyboards.
"""

from __future__ import annotations

from channels.base import IncomingMessage
from channels.telegram.keyboards import (
    main_menu_keyboard,
    parse_callback_data,
    voting_keyboard,
    voting_result_keyboard,
)
from app.logging import get_logger

logger = get_logger(__name__)

# Commands and their descriptions (for /ajuda and BotFather registration)
COMMANDS = {
    "/start": "Iniciar conversa com o Parlamentar de IA",
    "/ajuda": "Mostrar ajuda e comandos disponíveis",
    "/proposicoes": "Buscar proposições em tramitação",
    "/votar": "Ver proposições disponíveis para votação",
    "/agenda": "Ver agenda de votações do plenário",
    "/meuperfil": "Ver ou editar seu perfil de eleitor",
    "/meusvotos": "Ver histórico de seus votos populares",
    "/notificacoes": "Configurar frequência de notificações",
    "/deputados": "Buscar informações sobre deputados",
    "/premium": "Ver planos e assinar o Premium",
    "/menu": "Mostrar menu principal",
    "/reset": "Reiniciar conversa do zero",
}


async def handle_command(message: IncomingMessage) -> dict:
    """Route a command message to the appropriate response.

    Args:
        message: Incoming message starting with '/'.

    Returns:
        Dict with 'text' (response), optional 'buttons' (keyboard),
        and 'handled' (whether the command was a known command).
    """
    command = message.text.split()[0].lower().split("@")[0]  # strip @botname
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if command == "/start":
        return _handle_start(message)
    elif command == "/ajuda":
        return _handle_ajuda()
    elif command == "/premium":
        return await _handle_premium(message)
    elif command == "/menu":
        return _handle_menu()
    elif command == "/reset":
        return _handle_reset(message)
    else:
        # Known but agent-handled commands (/proposicoes, /votar, etc.)
        # Return as not handled so the handler routes to ADK agent
        return {"text": None, "buttons": None, "handled": False}


async def handle_callback(message: IncomingMessage) -> dict:
    """Route a callback query (button press) to the appropriate handler.

    Args:
        message: IncomingMessage with callback_data populated.

    Returns:
        Dict with 'text', optional 'buttons', 'callback_answer' (toast),
        and 'to_agent' (text to forward to agent if needed).
    """
    if not message.callback_data:
        return {"text": None, "buttons": None, "callback_answer": None, "to_agent": None}

    action, params = parse_callback_data(message.callback_data)

    if action == "voto" and len(params) >= 2:
        return _handle_voto_callback(params[0], params[1])

    elif action == "votar" and len(params) >= 1:
        return _handle_votar_prompt(params[0])

    elif action == "resultado" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando resultado...",
            "to_agent": f"Qual o resultado da votação popular da proposição {params[0]}?",
        }

    elif action == "tramitacao" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando tramitação...",
            "to_agent": f"Mostre a tramitação da proposição {params[0]}",
        }

    elif action == "analise" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando análise...",
            "to_agent": f"Mostre a análise IA da proposição {params[0]}",
        }

    elif action == "autores" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando autores...",
            "to_agent": f"Quem são os autores da proposição {params[0]}?",
        }

    elif action == "despesas" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando despesas...",
            "to_agent": f"Mostre as despesas do deputado {params[0]}",
        }

    elif action == "votacoes_dep" and len(params) >= 1:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Buscando votações...",
            "to_agent": f"Mostre as votações recentes do deputado {params[0]}",
        }

    elif action == "menu":
        return _handle_menu_callback(params[0] if params else "")

    elif action == "page":
        return _handle_pagination_callback(params)

    elif action in ("confirm", "cancel"):
        return _handle_confirmation_callback(action, params)

    elif action == "premium" and len(params) >= 2 and params[0] == "checkout":
        return await _handle_premium_checkout(message.chat_id, params[1])

    else:
        logger.warning("telegram.callback.unknown", action=action, params=params)
        return {
            "text": None,
            "buttons": None,
            "callback_answer": None,
            "to_agent": message.callback_data,
        }


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #

def _handle_start(message: IncomingMessage) -> dict:
    """Handle /start command — welcome message."""
    name = message.first_name or "eleitor(a)"
    text = (
        f"🏛️ <b>Olá, {name}!</b>\n\n"
        "Sou o <b>Parlamentar de IA</b> — seu assistente para acompanhar "
        "a Câmara dos Deputados.\n\n"
        "Posso te ajudar a:\n"
        "• 📜 Entender proposições em linguagem simples\n"
        "• 🗳️ Votar nas proposições que afetam sua vida\n"
        "• � Consultar a agenda de votações do plenário\n"
        "• 👤 Acompanhar deputados e seus gastos\n"
        "• 📊 Comparar o voto popular com a votação real\n"
        "• 🔔 Receber notificações sobre temas do seu interesse\n\n"
        "Basta me perguntar sobre qualquer assunto legislativo, "
        "ou use o <b>menu</b> abaixo para navegar. 👇"
    )
    return {"text": text, "buttons": main_menu_keyboard(), "handled": True}


def _handle_ajuda() -> dict:
    """Handle /ajuda command — list available commands."""
    lines = ["🆘 <b>Comandos disponíveis:</b>\n"]
    for cmd, desc in COMMANDS.items():
        lines.append(f"  {cmd} — {desc}")
    lines.append(
        "\nVocê também pode me enviar qualquer pergunta em linguagem natural. "
        "Eu entendo! 😊"
    )
    return {"text": "\n".join(lines), "buttons": None, "handled": True}


def _handle_menu() -> dict:
    """Handle /menu command — show main menu keyboard."""
    return {
        "text": "📋 <b>Menu Principal</b>\n\nEscolha uma opção:",
        "buttons": main_menu_keyboard(),
        "handled": True,
    }


async def _handle_premium(message: IncomingMessage) -> dict:
    """Handle /premium command — show plan info and upgrade options."""
    from channels.telegram.keyboards import premium_keyboard

    chat_id = message.chat_id
    plano = "GRATUITO"
    checkout_url = None

    try:
        from app.db.session import async_session_factory
        from sqlalchemy import select
        from app.domain.eleitor import Eleitor

        async with async_session_factory() as session:
            result = await session.execute(
                select(Eleitor.plano).where(Eleitor.chat_id == str(chat_id))
            )
            plano = result.scalar_one_or_none() or "GRATUITO"
    except Exception:
        pass

    if plano.upper() != "GRATUITO":
        text = (
            "⭐ <b>Parlamentaria Premium</b>\n\n"
            f"Você já é assinante do plano <b>{plano}</b>! 🎉\n\n"
            "Benefícios ativos:\n"
            "• ♾️ Perguntas ilimitadas\n"
            "• 🔍 Análise personalizada de proposições\n"
            "• 📊 Comparativo por região/UF\n"
            "• 📈 Relatório de alinhamento\n"
            "• 🔔 Alertas prioritários\n"
            "• 📚 Histórico completo\n\n"
            "Para gerenciar sua assinatura, me peça \"gerenciar assinatura\"."
        )
        return {"text": text, "buttons": None, "handled": True}

    text = (
        "⭐ <b>Parlamentaria Premium</b>\n\n"
        "Transforme sua participação democrática!\n\n"
        "<b>Plano Gratuito</b> (atual):\n"
        "• 5 perguntas por dia\n"
        "• Informações básicas\n\n"
        "<b>Plano Premium</b> — R$ 14,90/mês:\n"
        "• ♾️ Perguntas ilimitadas\n"
        "• 🔍 Análise personalizada de proposições\n"
        "• 📊 Comparativo de votos por região/UF\n"
        "• 📈 Relatório de alinhamento deputado vs popular\n"
        "• 🔔 Alertas prioritários\n"
        "• 📚 Histórico completo de votações\n\n"
        "💰 Ou economize com o <b>plano anual</b>: R$ 99,00/ano (45% off!)\n\n"
        "Escolha abaixo para assinar:"
    )
    return {"text": text, "buttons": premium_keyboard(), "handled": True}


def _handle_reset(message: IncomingMessage) -> dict:
    """Handle /reset command — will be processed by the webhook handler."""
    return {
        "text": (
            "🔄 Conversa reiniciada!\n\n"
            "Estou pronto para uma nova conversa. "
            "Como posso te ajudar?"
        ),
        "buttons": main_menu_keyboard(),
        "handled": True,
        "reset_session": True,
    }


# --------------------------------------------------------------------------- #
# Callback handlers
# --------------------------------------------------------------------------- #

def _handle_voto_callback(proposicao_id: str, voto: str) -> dict:
    """Handle inline vote button press — forward to agent as text command."""
    return {
        "text": None,
        "buttons": None,
        "callback_answer": f"Registrando voto {voto}...",
        "to_agent": f"Registrar meu voto {voto} na proposição {proposicao_id}",
    }


def _handle_votar_prompt(proposicao_id: str) -> dict:
    """Show voting keyboard for a proposition."""
    return {
        "text": f"🗳️ <b>Votação Popular — Proposição {proposicao_id}</b>\n\nEscolha sua posição:",
        "buttons": voting_keyboard(int(proposicao_id)),
        "callback_answer": None,
        "to_agent": None,
    }


def _handle_menu_callback(option: str) -> dict:
    """Route menu button presses to agent queries."""
    menu_queries = {
        "proposicoes": "Quais são as proposições em tramitação mais recentes?",
        "votar": "Quais proposições estão disponíveis para votação popular?",
        "deputados": "Como posso buscar informações sobre deputados?",
        "agenda": "Qual a agenda de votações do plenário para os próximos dias?",
        "meusvotos": "Mostre meu histórico de votos populares",
        "notificacoes": "Quais são minhas configurações de notificação? Mostre as opções disponíveis.",
        "perfil": "Mostre meu perfil de eleitor",
        "premium": None,  # handled as command
        "ajuda": None,  # handled directly
    }

    if option == "ajuda":
        return {
            "text": _handle_ajuda()["text"],
            "buttons": None,
            "callback_answer": None,
            "to_agent": None,
        }

    if option == "premium":
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Carregando Premium...",
            "to_agent": "/premium",
        }

    query = menu_queries.get(option, f"Menu: {option}")
    return {
        "text": None,
        "buttons": None,
        "callback_answer": "Processando...",
        "to_agent": query,
    }


def _handle_pagination_callback(params: list[str]) -> dict:
    """Handle pagination button presses."""
    if len(params) >= 2:
        command = params[0]
        page = params[1]
        return {
            "text": None,
            "buttons": None,
            "callback_answer": f"Página {page}...",
            "to_agent": f"Mostrar página {page} de {command}",
        }
    return {"text": None, "buttons": None, "callback_answer": None, "to_agent": None}


def _handle_confirmation_callback(action: str, params: list[str]) -> dict:
    """Handle confirm/cancel button presses."""
    if action == "confirm" and params:
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Confirmado!",
            "to_agent": f"Confirmar {':'.join(params)}",
        }
    return {
        "text": "❌ Ação cancelada.",
        "buttons": None,
        "callback_answer": "Cancelado",
        "to_agent": None,
    }


async def _handle_premium_checkout(chat_id: str, periodo: str) -> dict:
    """Handle premium checkout button press — generate Stripe checkout URL."""
    plano_slug = "cidadao_premium_anual" if periodo == "anual" else "cidadao_premium_mensal"

    try:
        from premium.agents.premium_tools import criar_checkout_session
        result = await criar_checkout_session(chat_id)

        if result.get("status") == "success" and result.get("checkout_url"):
            return {
                "text": (
                    "🔗 <b>Link de pagamento gerado!</b>\n\n"
                    f"Clique no link abaixo para assinar:\n{result['checkout_url']}\n\n"
                    "O link é seguro e processado pelo Stripe. "
                    "Após o pagamento, seu plano será ativado automaticamente! ✅"
                ),
                "buttons": None,
                "callback_answer": "Gerando link de pagamento...",
                "to_agent": None,
            }
        else:
            return {
                "text": None,
                "buttons": None,
                "callback_answer": "Erro ao gerar pagamento",
                "to_agent": f"Quero assinar o plano premium {periodo}",
            }
    except ImportError:
        return {
            "text": (
                "⚠️ O módulo de assinaturas não está disponível no momento.\n"
                "Tente novamente mais tarde."
            ),
            "buttons": None,
            "callback_answer": "Indisponível",
            "to_agent": None,
        }
    except Exception:
        logger.exception("premium_checkout.error")
        return {
            "text": None,
            "buttons": None,
            "callback_answer": "Erro",
            "to_agent": f"Quero assinar o plano premium {periodo}",
        }
