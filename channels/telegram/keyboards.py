"""Inline keyboard builders for Telegram interactions.

Provides reusable keyboard layouts for voting, navigation,
and other interactive flows in the Telegram channel.
"""

from __future__ import annotations

from channels.base import Button


# --------------------------------------------------------------------------- #
# Voting keyboards
# --------------------------------------------------------------------------- #

def voting_keyboard(proposicao_id: int) -> list[list[Button]]:
    """Build an inline keyboard for popular voting on a proposition.

    Args:
        proposicao_id: ID of the proposition being voted on.

    Returns:
        Rows of buttons: [SIM, NÃO, ABSTENÇÃO].
    """
    return [
        [
            Button(text="✅ SIM", callback_data=f"voto:{proposicao_id}:SIM"),
            Button(text="❌ NÃO", callback_data=f"voto:{proposicao_id}:NAO"),
            Button(text="⚪ ABSTENÇÃO", callback_data=f"voto:{proposicao_id}:ABSTENCAO"),
        ],
    ]


def voting_result_keyboard(proposicao_id: int) -> list[list[Button]]:
    """Build a keyboard to view voting results after casting a vote.

    Args:
        proposicao_id: ID of the proposition.

    Returns:
        Row with 'Ver Resultado' button.
    """
    return [
        [
            Button(
                text="📊 Ver Resultado",
                callback_data=f"resultado:{proposicao_id}",
            ),
        ],
    ]


# --------------------------------------------------------------------------- #
# Navigation keyboards
# --------------------------------------------------------------------------- #

def proposicao_actions_keyboard(proposicao_id: int) -> list[list[Button]]:
    """Build action buttons for a proposition detail view.

    Args:
        proposicao_id: ID of the proposition.

    Returns:
        Rows: [Votar, Tramitação] and [Análise IA, Autores].
    """
    return [
        [
            Button(text="🗳️ Votar", callback_data=f"votar:{proposicao_id}"),
            Button(text="📋 Tramitação", callback_data=f"tramitacao:{proposicao_id}"),
        ],
        [
            Button(text="🤖 Análise IA", callback_data=f"analise:{proposicao_id}"),
            Button(text="👥 Autores", callback_data=f"autores:{proposicao_id}"),
        ],
    ]


def deputado_actions_keyboard(deputado_id: int) -> list[list[Button]]:
    """Build action buttons for a deputy profile.

    Args:
        deputado_id: ID of the deputy.

    Returns:
        Rows: [Despesas, Votações].
    """
    return [
        [
            Button(text="💰 Despesas", callback_data=f"despesas:{deputado_id}"),
            Button(text="📊 Votações", callback_data=f"votacoes_dep:{deputado_id}"),
        ],
    ]


def pagination_keyboard(
    command: str, current_page: int, has_next: bool
) -> list[list[Button]]:
    """Build pagination buttons for list results.

    Args:
        command: Base command for pagination (e.g., 'proposicoes', 'deputados').
        current_page: Current page number (1-based).
        has_next: Whether there's a next page.

    Returns:
        Row with Previous/Next buttons as applicable.
    """
    buttons: list[Button] = []

    if current_page > 1:
        buttons.append(
            Button(text="⬅️ Anterior", callback_data=f"page:{command}:{current_page - 1}")
        )

    if has_next:
        buttons.append(
            Button(text="➡️ Próxima", callback_data=f"page:{command}:{current_page + 1}")
        )

    return [buttons] if buttons else []


# --------------------------------------------------------------------------- #
# Menu/Settings keyboards
# --------------------------------------------------------------------------- #

def main_menu_keyboard() -> list[list[Button]]:
    """Build the main menu inline keyboard.

    Returns:
        Rows of main menu options.
    """
    return [
        [
            Button(text="📜 Proposições", callback_data="menu:proposicoes"),
            Button(text="🗳️ Votar", callback_data="menu:votar"),
        ],
        [
            Button(text="👤 Deputados", callback_data="menu:deputados"),
            Button(text="� Agenda", callback_data="menu:agenda"),
        ],
        [
            Button(text="📊 Meus Votos", callback_data="menu:meusvotos"),
            Button(text="🔔 Notificações", callback_data="menu:notificacoes"),
        ],
        [
            Button(text="⭐ Premium", callback_data="menu:premium"),
            Button(text="⚙️ Meu Perfil", callback_data="menu:perfil"),
        ],
        [
            Button(text="❓ Ajuda", callback_data="menu:ajuda"),
        ],
    ]


def premium_keyboard() -> list[list[Button]]:
    """Build the premium subscription keyboard.

    Returns:
        Rows with subscription options.
    """
    return [
        [
            Button(text="💳 Assinar Mensal (R$ 14,90)", callback_data="premium:checkout:mensal"),
        ],
        [
            Button(text="💰 Assinar Anual (R$ 99,00)", callback_data="premium:checkout:anual"),
        ],
        [
            Button(text="⬅️ Voltar ao Menu", callback_data="menu:main"),
        ],
    ]


def confirm_keyboard(action: str, target_id: str = "") -> list[list[Button]]:
    """Build a confirmation keyboard (Sim/Não).

    Args:
        action: Action to confirm (e.g., 'cadastro', 'reset').
        target_id: Optional target identifier.

    Returns:
        Row with Confirmar/Cancelar buttons.
    """
    suffix = f":{target_id}" if target_id else ""
    return [
        [
            Button(text="✅ Confirmar", callback_data=f"confirm:{action}{suffix}"),
            Button(text="❌ Cancelar", callback_data=f"cancel:{action}{suffix}"),
        ],
    ]


# --------------------------------------------------------------------------- #
# Callback data parsing
# --------------------------------------------------------------------------- #

def parse_callback_data(data: str) -> tuple[str, list[str]]:
    """Parse structured callback data into action and parameters.

    Callback data format: 'action:param1:param2:...'

    Args:
        data: Raw callback data string.

    Returns:
        Tuple of (action, [params]).

    Examples:
        >>> parse_callback_data("voto:1234:SIM")
        ('voto', ['1234', 'SIM'])
        >>> parse_callback_data("menu:proposicoes")
        ('menu', ['proposicoes'])
    """
    parts = data.split(":")
    action = parts[0]
    params = parts[1:] if len(parts) > 1 else []
    return action, params
