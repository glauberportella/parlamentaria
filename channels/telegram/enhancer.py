"""Telegram response enhancer — enriches agent responses with interactive buttons.

The ADK agent returns pure text, but Telegram supports rich interactions
through Inline Keyboards. This module analyses agent responses, detects
context (proposition IDs, voting confirmations, deputy mentions, etc.)
and attaches the appropriate interactive buttons.

This keeps the agent layer channel-agnostic while giving Telegram users
a much richer experience with tap-to-vote, navigation buttons, etc.
"""

from __future__ import annotations

import re

from channels.base import Button
from channels.telegram.keyboards import (
    proposicao_actions_keyboard,
    voting_keyboard,
    voting_result_keyboard,
    deputado_actions_keyboard,
)


# --------------------------------------------------------------------------- #
# Regex patterns to detect proposição IDs in agent text
# --------------------------------------------------------------------------- #

# Matches patterns like: "proposição 1234", "PL 1234/2026", "proposição ID 1234"
_RE_PROPOSICAO_ID = re.compile(
    r"(?:proposi[çc][ãa]o\s+(?:ID\s*)?(\d{4,}))"
    r"|(?:(?:PL|PEC|MPV|PLP|PDL|PRC)\s+\d+/\d{4}\s*\(ID[:\s]*(\d+)\))"
    r"|(?:proposi[çc][ãa]o\s+(\d{4,})/\d{4})",
    re.IGNORECASE,
)

# Matches explicit mention of a proposição together with its numeric ID
# e.g. "PL 1234/2026" when agent embeds proposicao_id in parenthesis
_RE_PROP_WITH_SIGLA = re.compile(
    r"(?:PL|PEC|MPV|PLP|PDL|PRC)\s+(\d+)/(\d{4})",
    re.IGNORECASE,
)

# Matches "voto SIM registrado" / "voto registrado" patterns
_RE_VOTO_REGISTRADO = re.compile(
    r"voto\s+(?:SIM|NAO|NÃO|ABSTENCAO|ABSTENÇÃO)?\s*registrado",
    re.IGNORECASE,
)

# Matches "deputado(a)" followed by a name, with optional ID
_RE_DEPUTADO_ID = re.compile(
    r"deputad[oa]\s+.*?\(ID[:\s]*(\d+)\)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def enhance_response(
    agent_text: str,
    user_text: str = "",
) -> tuple[str, list[list[Button]] | None]:
    """Analyse an agent response and attach contextual inline buttons.

    The function inspects the agent text for known patterns and decides
    which keyboard to attach:

    1. **Vote registered** → "Ver Resultado" button
    2. **Single proposição detail** → Action buttons (Votar, Tramitação, …)
    3. **Proposição listing** → No buttons (too many to pick one)
    4. **Deputy detail** → Deputy action buttons
    5. **Voting prompt / "deseja votar?"** → Voting keyboard (SIM / NÃO / ABSTENÇÃO)

    Args:
        agent_text: The formatted agent response text.
        user_text: The original user message (helps disambiguate intent).

    Returns:
        Tuple of ``(text, buttons)`` where ``buttons`` may be ``None``.
    """
    if not agent_text:
        return agent_text, None

    # Priority 1 — vote was just registered → show result button
    prop_id = _detect_vote_registered(agent_text)
    if prop_id:
        return agent_text, voting_result_keyboard(prop_id)

    # Priority 2 — agent is prompting the user to vote → show voting keyboard
    prop_id = _detect_voting_prompt(agent_text, user_text)
    if prop_id:
        return agent_text, voting_keyboard(prop_id)

    # Priority 3 — single proposição detail → action buttons
    prop_id = _detect_single_proposicao(agent_text)
    if prop_id:
        return agent_text, proposicao_actions_keyboard(prop_id)

    # Priority 4 — deputy detail → deputy action buttons
    dep_id = _detect_single_deputado(agent_text)
    if dep_id:
        return agent_text, deputado_actions_keyboard(dep_id)

    # No enhancement
    return agent_text, None


# --------------------------------------------------------------------------- #
# Detection helpers
# --------------------------------------------------------------------------- #


def _extract_proposicao_ids(text: str) -> list[int]:
    """Extract all proposição IDs found in text.

    Returns:
        List of integer IDs (deduplicated, ordered by appearance).
    """
    ids: list[int] = []
    for m in _RE_PROPOSICAO_ID.finditer(text):
        for g in m.groups():
            if g:
                pid = int(g)
                if pid not in ids:
                    ids.append(pid)
    return ids


def _detect_vote_registered(text: str) -> int | None:
    """Detect if the agent confirmed a vote was registered.

    Returns:
        The proposição ID if a vote confirmation is found, else None.
    """
    if not _RE_VOTO_REGISTRADO.search(text):
        return None
    ids = _extract_proposicao_ids(text)
    return ids[0] if ids else None


def _detect_voting_prompt(text: str, user_text: str) -> int | None:
    """Detect if the agent is prompting the user to vote.

    Triggers on phrases like "deseja votar", "registre seu voto",
    "qual o seu voto", etc.

    Returns:
        The proposição ID if a voting prompt is found, else None.
    """
    voting_phrases = (
        "deseja votar",
        "quer votar",
        "registre seu voto",
        "registrar seu voto",
        "qual o seu voto",
        "qual seu voto",
        "gostaria de votar",
        "vote agora",
        "pode votar",
    )
    text_lower = text.lower()
    if not any(phrase in text_lower for phrase in voting_phrases):
        return None
    ids = _extract_proposicao_ids(text)
    return ids[0] if ids else None


def _detect_single_proposicao(text: str) -> int | None:
    """Detect if the response describes a single proposição in detail.

    Heuristic: exactly one proposição ID is mentioned and the text
    contains detail markers like "ementa", "situação", "autor", "tema".

    Returns:
        The proposição ID or None.
    """
    ids = _extract_proposicao_ids(text)
    if len(ids) != 1:
        return None

    detail_markers = ("ementa", "situação", "situacao", "autor", "tema", "tramitação", "tramitacao", "apresentação", "apresentacao", "resumo")
    text_lower = text.lower()
    matches = sum(1 for marker in detail_markers if marker in text_lower)
    if matches >= 2:
        return ids[0]

    return None


def _detect_single_deputado(text: str) -> int | None:
    """Detect if the response describes a single deputy.

    Returns:
        The deputy ID or None.
    """
    matches = _RE_DEPUTADO_ID.findall(text)
    if len(matches) == 1:
        return int(matches[0])
    return None
