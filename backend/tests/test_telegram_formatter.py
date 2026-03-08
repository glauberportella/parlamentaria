"""Tests for channels.telegram.formatter — Markdown → Telegram HTML conversion."""

import pytest

from channels.telegram.formatter import (
    TELEGRAM_MAX_MESSAGE_LENGTH,
    format_agent_response,
    markdown_to_telegram_html,
    split_message,
)


# ====================================================================== #
# markdown_to_telegram_html                                               #
# ====================================================================== #


class TestMarkdownToTelegramHTML:
    """Unit tests for the Markdown-to-HTML converter."""

    # -- empty / trivial input --

    def test_empty_string(self):
        assert markdown_to_telegram_html("") == ""

    def test_plain_text_unchanged(self):
        assert markdown_to_telegram_html("Olá mundo") == "Olá mundo"

    # -- bold --

    def test_bold_double_asterisk(self):
        assert markdown_to_telegram_html("**bold**") == "<b>bold</b>"

    def test_bold_double_underscore(self):
        assert markdown_to_telegram_html("__bold__") == "<b>bold</b>"

    def test_bold_within_sentence(self):
        result = markdown_to_telegram_html("Isso é **importante** mesmo")
        assert result == "Isso é <b>importante</b> mesmo"

    def test_multiple_bold(self):
        result = markdown_to_telegram_html("**a** e **b**")
        assert "<b>a</b>" in result
        assert "<b>b</b>" in result

    # -- italic --

    def test_italic_single_asterisk(self):
        assert markdown_to_telegram_html("*italic*") == "<i>italic</i>"

    def test_italic_single_underscore(self):
        assert markdown_to_telegram_html("_italic_") == "<i>italic</i>"

    def test_italic_not_inside_word(self):
        """Underscores inside variable_names should NOT become italic."""
        result = markdown_to_telegram_html("some_variable_name")
        assert "<i>" not in result

    # -- bold + italic --

    def test_bold_and_italic_together(self):
        result = markdown_to_telegram_html("**bold** and *italic*")
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result

    def test_triple_asterisk_bold_italic(self):
        result = markdown_to_telegram_html("***bold italic***")
        assert "<b>" in result
        assert "<i>" in result

    # -- strikethrough --

    def test_strikethrough(self):
        assert markdown_to_telegram_html("~~strike~~") == "<s>strike</s>"

    # -- inline code --

    def test_inline_code(self):
        assert markdown_to_telegram_html("`code`") == "<code>code</code>"

    def test_inline_code_special_chars(self):
        result = markdown_to_telegram_html("`a < b`")
        assert "<code>a &lt; b</code>" in result

    def test_inline_code_not_converted_by_bold(self):
        """Bold markers inside code should NOT be parsed."""
        result = markdown_to_telegram_html("`**not bold**`")
        assert "<b>" not in result
        assert "<code>" in result

    # -- code blocks --

    def test_fenced_code_block(self):
        text = "```\nprint('hello')\n```"
        result = markdown_to_telegram_html(text)
        assert "<pre>" in result
        assert "print" in result

    def test_fenced_code_block_with_language(self):
        text = "```python\nprint('hello')\n```"
        result = markdown_to_telegram_html(text)
        assert 'language-python' in result
        assert "<pre>" in result

    def test_code_block_html_escaped(self):
        text = "```\n<script>alert('xss')</script>\n```"
        result = markdown_to_telegram_html(text)
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    # -- links --

    def test_markdown_link(self):
        result = markdown_to_telegram_html("[Google](https://google.com)")
        assert '<a href="https://google.com">Google</a>' in result

    def test_link_with_text(self):
        result = markdown_to_telegram_html("Veja [aqui](https://example.com) para mais")
        assert '<a href="https://example.com">aqui</a>' in result

    # -- headings --

    def test_h1(self):
        result = markdown_to_telegram_html("# Título")
        assert "<b>Título</b>" in result

    def test_h3(self):
        result = markdown_to_telegram_html("### Subtítulo")
        assert "<b>Subtítulo</b>" in result

    def test_heading_not_midline(self):
        """Hash in the middle of a line should not become a heading."""
        result = markdown_to_telegram_html("issue #42 is important")
        assert "<b>" not in result

    # -- horizontal rules --

    def test_horizontal_rule_dashes(self):
        result = markdown_to_telegram_html("before\n---\nafter")
        assert "━" in result

    def test_horizontal_rule_asterisks(self):
        result = markdown_to_telegram_html("***")
        # Three asterisks on their own line = horizontal rule
        assert "━" in result

    # -- unordered lists --

    def test_bullet_asterisk(self):
        text = "* item 1\n* item 2"
        result = markdown_to_telegram_html(text)
        assert "• item 1" in result
        assert "• item 2" in result

    def test_bullet_dash(self):
        text = "- item A\n- item B"
        result = markdown_to_telegram_html(text)
        assert "• item A" in result

    def test_bullet_plus(self):
        text = "+ item"
        result = markdown_to_telegram_html(text)
        assert "• item" in result

    def test_list_item_with_bold(self):
        """Bullet list items with bold formatting inside."""
        text = "*   **Nome:** Glauber"
        result = markdown_to_telegram_html(text)
        assert "•" in result
        assert "<b>Nome:</b>" in result

    def test_list_multiple_items_with_bold(self):
        text = (
            "*   **Nome Completo:** Glauber\n"
            "*   **Estado (UF):** MG\n"
            "*   **Cidadão Brasileiro:** Sim"
        )
        result = markdown_to_telegram_html(text)
        assert result.count("•") == 3
        assert "<b>Nome Completo:</b>" in result
        assert "<b>Estado (UF):</b>" in result
        assert "<b>Cidadão Brasileiro:</b>" in result

    # -- blockquotes --

    def test_blockquote_single_line(self):
        result = markdown_to_telegram_html("> citação")
        assert "<blockquote>" in result
        assert "citação" in result

    def test_blockquote_multi_line_merged(self):
        text = "> linha 1\n> linha 2"
        result = markdown_to_telegram_html(text)
        assert result.count("<blockquote>") == 1
        assert "linha 1" in result
        assert "linha 2" in result

    # -- HTML escaping --

    def test_html_entities_escaped(self):
        result = markdown_to_telegram_html("a < b > c & d")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

    def test_html_tags_in_text_escaped(self):
        result = markdown_to_telegram_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    # -- whitespace cleanup --

    def test_excess_blank_lines_collapsed(self):
        text = "a\n\n\n\n\nb"
        result = markdown_to_telegram_html(text)
        assert "\n\n\n" not in result
        assert "a\n\nb" == result

    # -- real-world agent response --

    def test_real_profile_response(self):
        """Test with a real-world agent response (the user's exact example)."""
        text = (
            "Olá, Glauber! Aqui estão os detalhes do seu perfil:\n\n"
            "*   **Nome Completo:** Glauber Portella Ornelas de Melo\n"
            "*   **Estado (UF):** MG\n"
            "*   **Cidadão Brasileiro:** Sim\n"
            "*   **Data de Nascimento:** 12/01/1982\n"
            "*   **CPF Registrado:** Sim (armazenado como hash)\n"
            "*   **Nível de Verificação:** AUTO_DECLARADO (Seus votos contam como OFICIAIS)\n"
            "*   **Título de Eleitor Registrado:** Não\n"
            "*   **Temas de Interesse para Notificações:** Nenhum tema configurado.\n\n"
            "Você é elegível para voto oficial!\n\n"
            "Para aumentar a confiança do seu voto para o nível máximo "
            "(**VERIFICADO_TITULO**), você pode validar seu título de "
            "eleitor usando o comando `/verificar`.\n\n"
            "Gostaria de atualizar alguma informação do seu perfil ou "
            "configurar seus temas de interesse?"
        )
        result = markdown_to_telegram_html(text)

        # Bullets
        assert result.count("•") == 8

        # Bold labels
        assert "<b>Nome Completo:</b>" in result
        assert "<b>Estado (UF):</b>" in result
        assert "<b>Nível de Verificação:</b>" in result

        # Bold inline reference
        assert "<b>VERIFICADO_TITULO</b>" in result

        # Inline code for /command
        assert "<code>/verificar</code>" in result

        # No raw markdown artifacts left
        assert "**" not in result
        assert "*   " not in result

    def test_proposicao_summary_response(self):
        """Test a typical proposição summary response."""
        text = (
            "## PL 1234/2026 — Reforma Tributária\n\n"
            "**Resumo:** Esta proposição visa reformar o sistema tributário.\n\n"
            "### Pontos Principais\n\n"
            "- Simplificação de impostos\n"
            "- Redução de carga para MEIs\n"
            "- Novo imposto sobre grandes fortunas\n\n"
            "**Situação:** Em tramitação\n\n"
            "Use `/votar` para registrar sua opinião."
        )
        result = markdown_to_telegram_html(text)

        assert "<b>PL 1234/2026 — Reforma Tributária</b>" in result
        assert "<b>Pontos Principais</b>" in result
        assert "• Simplificação de impostos" in result
        assert "<b>Resumo:</b>" in result
        assert "<code>/votar</code>" in result


# ====================================================================== #
# split_message                                                           #
# ====================================================================== #


class TestSplitMessage:
    """Unit tests for the message splitter."""

    def test_empty_returns_empty_list(self):
        assert split_message("") == []

    def test_none_returns_empty_list(self):
        assert split_message(None) == []

    def test_short_message_single_chunk(self):
        assert split_message("hello") == ["hello"]

    def test_exact_limit(self):
        text = "a" * TELEGRAM_MAX_MESSAGE_LENGTH
        assert split_message(text) == [text]

    def test_splits_at_paragraph(self):
        part1 = "a" * 3000
        part2 = "b" * 3000
        text = part1 + "\n\n" + part2
        chunks = split_message(text)
        assert len(chunks) == 2
        assert chunks[0] == part1
        assert chunks[1] == part2

    def test_splits_at_newline_when_no_paragraph(self):
        part1 = "a" * 3000
        part2 = "b" * 3000
        text = part1 + "\n" + part2
        chunks = split_message(text)
        assert len(chunks) == 2

    def test_splits_at_space_when_no_newline(self):
        word = "a" * 100
        text = " ".join([word] * 50)  # ~5050 chars
        chunks = split_message(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= TELEGRAM_MAX_MESSAGE_LENGTH

    def test_hard_cut_no_break_points(self):
        text = "a" * 5000
        chunks = split_message(text)
        assert len(chunks) == 2
        assert chunks[0] == "a" * TELEGRAM_MAX_MESSAGE_LENGTH
        assert chunks[1] == "a" * (5000 - TELEGRAM_MAX_MESSAGE_LENGTH)

    def test_custom_max_length(self):
        text = "hello world foo bar"
        chunks = split_message(text, max_length=11)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 11

    def test_multiple_splits(self):
        part = "x" * 3000
        text = f"{part}\n\n{part}\n\n{part}"
        chunks = split_message(text)
        assert len(chunks) == 3


# ====================================================================== #
# format_agent_response                                                   #
# ====================================================================== #


class TestFormatAgentResponse:
    """Tests for the safe wrapper."""

    def test_normal_conversion(self):
        assert "<b>bold</b>" in format_agent_response("**bold**")

    def test_empty_string(self):
        assert format_agent_response("") == ""

    def test_none_returns_none(self):
        assert format_agent_response(None) is None

    def test_fallback_on_error(self):
        """If markdown_to_telegram_html raises, should escape and return."""
        from unittest.mock import patch

        with patch(
            "channels.telegram.formatter.markdown_to_telegram_html",
            side_effect=RuntimeError("boom"),
        ):
            result = format_agent_response("<b>test</b>")
            # Should be escaped, not raise
            assert "&lt;b&gt;" in result
