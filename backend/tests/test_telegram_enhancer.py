"""Tests for channels.telegram.enhancer — response enhancement with buttons."""

import pytest

from channels.base import Button
from channels.telegram.enhancer import (
    enhance_response,
    _extract_proposicao_ids,
    _detect_vote_registered,
    _detect_voting_prompt,
    _detect_single_proposicao,
    _detect_single_deputado,
)


# ====================================================================== #
# _extract_proposicao_ids                                                 #
# ====================================================================== #


class TestExtractProposicaoIds:
    """Tests for ID extraction from text."""

    def test_simple_proposicao_id(self):
        assert _extract_proposicao_ids("proposição 1234") == [1234]

    def test_proposicao_id_with_uppercase(self):
        assert _extract_proposicao_ids("Proposição 5678") == [5678]

    def test_proposicao_id_accent_variant(self):
        assert _extract_proposicao_ids("proposicao 9999") == [9999]

    def test_proposicao_with_id_prefix(self):
        assert _extract_proposicao_ids("proposição ID 4321") == [4321]

    def test_pl_with_parenthesized_id(self):
        assert _extract_proposicao_ids("PL 100/2026 (ID: 1234)") == [1234]

    def test_pec_with_parenthesized_id(self):
        assert _extract_proposicao_ids("PEC 45/2025 (ID 9876)") == [9876]

    def test_no_match(self):
        assert _extract_proposicao_ids("nenhum ID aqui") == []

    def test_multiple_ids(self):
        text = "proposição 1111 e proposição 2222"
        ids = _extract_proposicao_ids(text)
        assert 1111 in ids
        assert 2222 in ids

    def test_deduplication(self):
        text = "proposição 1234 ... proposição 1234"
        assert _extract_proposicao_ids(text) == [1234]

    def test_short_numbers_ignored(self):
        """Numbers shorter than 4 digits are not proposição IDs."""
        assert _extract_proposicao_ids("proposição 12") == []


# ====================================================================== #
# _detect_vote_registered                                                 #
# ====================================================================== #


class TestDetectVoteRegistered:
    """Tests for vote confirmation detection."""

    def test_voto_sim_registrado(self):
        text = "Voto SIM registrado com sucesso para a proposição 1234!"
        assert _detect_vote_registered(text) == 1234

    def test_voto_nao_registrado(self):
        text = "Voto NAO registrado na proposição 5678."
        assert _detect_vote_registered(text) == 5678

    def test_voto_abstencao_registrado(self):
        text = "Voto ABSTENÇÃO registrado para a proposição 9999."
        assert _detect_vote_registered(text) == 9999

    def test_no_voto_pattern(self):
        assert _detect_vote_registered("Esta é uma análise da proposição 1234.") is None

    def test_voto_pattern_but_no_id(self):
        assert _detect_vote_registered("Voto SIM registrado com sucesso!") is None


# ====================================================================== #
# _detect_voting_prompt                                                   #
# ====================================================================== #


class TestDetectVotingPrompt:
    """Tests for voting prompt detection."""

    def test_deseja_votar(self):
        text = "Você deseja votar na proposição 1234?"
        assert _detect_voting_prompt(text, "") == 1234

    def test_quer_votar(self):
        text = "Quer votar na proposição 5678?"
        assert _detect_voting_prompt(text, "") == 5678

    def test_registre_seu_voto(self):
        text = "Registre seu voto na proposição 9999."
        assert _detect_voting_prompt(text, "") == 9999

    def test_gostaria_de_votar(self):
        text = "Gostaria de votar nesta proposição 4444?"
        assert _detect_voting_prompt(text, "") == 4444

    def test_no_voting_phrase(self):
        text = "Detalhes da proposição 1234."
        assert _detect_voting_prompt(text, "") is None

    def test_voting_phrase_but_no_id(self):
        assert _detect_voting_prompt("Deseja votar?", "") is None


# ====================================================================== #
# _detect_single_proposicao                                               #
# ====================================================================== #


class TestDetectSingleProposicao:
    """Tests for single proposição detail detection."""

    def test_single_with_detail_markers(self):
        text = (
            "Proposição 1234\n"
            "Ementa: Reforma tributária.\n"
            "Situação: Em tramitação.\n"
            "Autor: Dep. Fulano."
        )
        assert _detect_single_proposicao(text) == 1234

    def test_multiple_ids_returns_none(self):
        text = "Proposição 1111 e proposição 2222 com ementa e situação."
        assert _detect_single_proposicao(text) is None

    def test_single_id_but_no_detail(self):
        text = "Proposição 1234 foi mencionada."
        assert _detect_single_proposicao(text) is None

    def test_single_with_resumo_and_tema(self):
        text = (
            "Proposição 5678\n"
            "Resumo: Algo importante.\n"
            "Tema: Educação"
        )
        assert _detect_single_proposicao(text) == 5678


# ====================================================================== #
# _detect_single_deputado                                                 #
# ====================================================================== #


class TestDetectSingleDeputado:
    """Tests for deputy detection."""

    def test_single_deputy(self):
        text = "Deputado Fulano de Tal (ID: 12345) - PT/SP"
        assert _detect_single_deputado(text) == 12345

    def test_deputada(self):
        text = "Deputada Maria Silva (ID 67890)"
        assert _detect_single_deputado(text) == 67890

    def test_multiple_deputies_returns_none(self):
        text = "Deputado A (ID: 111) e Deputado B (ID: 222)"
        assert _detect_single_deputado(text) is None

    def test_no_deputy(self):
        assert _detect_single_deputado("Nenhum deputado aqui.") is None


# ====================================================================== #
# enhance_response (integration)                                          #
# ====================================================================== #


class TestEnhanceResponse:
    """Integration tests for the full enhance_response function."""

    def test_empty_text(self):
        text, buttons = enhance_response("")
        assert text == ""
        assert buttons is None

    def test_none_text(self):
        text, buttons = enhance_response(None)
        assert text is None
        assert buttons is None

    def test_plain_text_no_buttons(self):
        text, buttons = enhance_response("Olá! Como posso te ajudar?")
        assert text == "Olá! Como posso te ajudar?"
        assert buttons is None

    def test_vote_registered_shows_result_button(self):
        agent_text = (
            "Voto SIM registrado com sucesso para a proposição 1234!\n"
            "Seu voto é do tipo OFICIAL."
        )
        text, buttons = enhance_response(agent_text)
        assert text == agent_text
        assert buttons is not None
        # Should be a "Ver Resultado" button
        flat = [btn for row in buttons for btn in row]
        assert any("resultado" in btn.callback_data for btn in flat)

    def test_voting_prompt_shows_voting_keyboard(self):
        agent_text = "Você deseja votar na proposição 1234?"
        text, buttons = enhance_response(agent_text)
        assert buttons is not None
        flat = [btn for row in buttons for btn in row]
        callback_datas = [btn.callback_data for btn in flat]
        assert "voto:1234:SIM" in callback_datas
        assert "voto:1234:NAO" in callback_datas
        assert "voto:1234:ABSTENCAO" in callback_datas

    def test_proposicao_detail_shows_action_buttons(self):
        agent_text = (
            "Proposição 5678\n\n"
            "Ementa: Reforma educacional.\n"
            "Situação: Em tramitação.\n"
            "Autor: Dep. Cicrano de Tal."
        )
        text, buttons = enhance_response(agent_text)
        assert buttons is not None
        flat = [btn for row in buttons for btn in row]
        callback_datas = [btn.callback_data for btn in flat]
        assert any("votar:5678" in cd for cd in callback_datas)
        assert any("tramitacao:5678" in cd for cd in callback_datas)

    def test_deputy_detail_shows_deputy_buttons(self):
        agent_text = "Deputado João Silva (ID: 99999) - PL/RJ. Partido Liberal."
        text, buttons = enhance_response(agent_text)
        assert buttons is not None
        flat = [btn for row in buttons for btn in row]
        callback_datas = [btn.callback_data for btn in flat]
        assert any("despesas:99999" in cd for cd in callback_datas)
        assert any("votacoes_dep:99999" in cd for cd in callback_datas)

    def test_priority_vote_registered_over_proposicao_detail(self):
        """Vote confirmation takes priority over proposição detail."""
        agent_text = (
            "Voto SIM registrado com sucesso para a proposição 1234!\n"
            "Ementa: Reforma tributária.\n"
            "Situação: Em tramitação."
        )
        text, buttons = enhance_response(agent_text)
        # Should show "Ver Resultado", NOT action buttons
        flat = [btn for row in buttons for btn in row]
        assert any("resultado" in btn.callback_data for btn in flat)
        assert not any("votar:" in btn.callback_data for btn in flat)

    def test_priority_voting_prompt_over_detail(self):
        """Voting prompt takes priority over mere detail."""
        agent_text = (
            "Proposição 1234 — Reforma tributária\n"
            "Ementa: blá blá\n"
            "Situação: Em tramitação.\n\n"
            "Você deseja votar nesta proposição 1234?"
        )
        text, buttons = enhance_response(agent_text)
        flat = [btn for row in buttons for btn in row]
        assert any("voto:1234:SIM" in btn.callback_data for btn in flat)

    def test_listing_no_buttons(self):
        """Multiple proposições listed should NOT get buttons."""
        agent_text = (
            "Proposições recentes:\n"
            "1. Proposição 1111 — Educação\n"
            "2. Proposição 2222 — Saúde\n"
            "3. Proposição 3333 — Economia"
        )
        text, buttons = enhance_response(agent_text)
        assert buttons is None

    def test_text_preserved(self):
        """The original text must never be modified."""
        original = "Voto SIM registrado para a proposição 1234!"
        text, _ = enhance_response(original)
        assert text == original
