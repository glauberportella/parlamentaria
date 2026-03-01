"""Tests for the Telegram channel adapter, handlers, keyboards, and webhook."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from channels.base import Button, IncomingMessage
from channels.telegram.keyboards import (
    confirm_keyboard,
    deputado_actions_keyboard,
    main_menu_keyboard,
    pagination_keyboard,
    parse_callback_data,
    proposicao_actions_keyboard,
    voting_keyboard,
    voting_result_keyboard,
)
from channels.telegram.handlers import (
    COMMANDS,
    handle_callback,
    handle_command,
)


# ====================================================================== #
# Keyboards                                                               #
# ====================================================================== #


class TestVotingKeyboard:
    """Tests for voting keyboard builder."""

    def test_voting_keyboard_has_three_buttons(self):
        rows = voting_keyboard(1234)
        assert len(rows) == 1
        assert len(rows[0]) == 3

    def test_voting_keyboard_callback_data(self):
        rows = voting_keyboard(999)
        buttons = rows[0]
        assert buttons[0].callback_data == "voto:999:SIM"
        assert buttons[1].callback_data == "voto:999:NAO"
        assert buttons[2].callback_data == "voto:999:ABSTENCAO"

    def test_voting_keyboard_button_text(self):
        rows = voting_keyboard(1)
        buttons = rows[0]
        assert "SIM" in buttons[0].text
        assert "NÃO" in buttons[1].text
        assert "ABSTENÇÃO" in buttons[2].text

    def test_voting_keyboard_returns_button_instances(self):
        rows = voting_keyboard(42)
        for btn in rows[0]:
            assert isinstance(btn, Button)


class TestVotingResultKeyboard:
    """Tests for voting result keyboard builder."""

    def test_result_keyboard_has_one_button(self):
        rows = voting_result_keyboard(123)
        assert len(rows) == 1
        assert len(rows[0]) == 1

    def test_result_keyboard_callback_data(self):
        rows = voting_result_keyboard(456)
        assert rows[0][0].callback_data == "resultado:456"


class TestProposicaoActionsKeyboard:
    """Tests for proposition action buttons."""

    def test_has_two_rows(self):
        rows = proposicao_actions_keyboard(100)
        assert len(rows) == 2

    def test_first_row_has_votar_and_tramitacao(self):
        rows = proposicao_actions_keyboard(100)
        callbacks = [b.callback_data for b in rows[0]]
        assert "votar:100" in callbacks
        assert "tramitacao:100" in callbacks

    def test_second_row_has_analise_and_autores(self):
        rows = proposicao_actions_keyboard(100)
        callbacks = [b.callback_data for b in rows[1]]
        assert "analise:100" in callbacks
        assert "autores:100" in callbacks


class TestDeputadoActionsKeyboard:
    """Tests for deputy action buttons."""

    def test_has_one_row(self):
        rows = deputado_actions_keyboard(50)
        assert len(rows) == 1

    def test_has_despesas_and_votacoes(self):
        rows = deputado_actions_keyboard(50)
        callbacks = [b.callback_data for b in rows[0]]
        assert "despesas:50" in callbacks
        assert "votacoes_dep:50" in callbacks


class TestPaginationKeyboard:
    """Tests for pagination keyboard."""

    def test_first_page_only_next(self):
        rows = pagination_keyboard("proposicoes", current_page=1, has_next=True)
        assert len(rows) == 1
        assert len(rows[0]) == 1
        assert "page:proposicoes:2" == rows[0][0].callback_data

    def test_middle_page_both_buttons(self):
        rows = pagination_keyboard("proposicoes", current_page=3, has_next=True)
        assert len(rows[0]) == 2
        assert "page:proposicoes:2" == rows[0][0].callback_data
        assert "page:proposicoes:4" == rows[0][1].callback_data

    def test_last_page_only_previous(self):
        rows = pagination_keyboard("deputados", current_page=5, has_next=False)
        assert len(rows[0]) == 1
        assert "page:deputados:4" == rows[0][0].callback_data

    def test_single_page_no_buttons(self):
        rows = pagination_keyboard("x", current_page=1, has_next=False)
        assert rows == []


class TestMainMenuKeyboard:
    """Tests for main menu keyboard."""

    def test_has_three_rows(self):
        rows = main_menu_keyboard()
        assert len(rows) == 3

    def test_all_are_button_instances(self):
        rows = main_menu_keyboard()
        for row in rows:
            for btn in row:
                assert isinstance(btn, Button)

    def test_contains_proposicoes_option(self):
        rows = main_menu_keyboard()
        all_callbacks = [btn.callback_data for row in rows for btn in row]
        assert "menu:proposicoes" in all_callbacks


class TestConfirmKeyboard:
    """Tests for confirmation keyboard."""

    def test_has_two_buttons(self):
        rows = confirm_keyboard("cadastro")
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_confirm_cancel_callbacks(self):
        rows = confirm_keyboard("cadastro", "123")
        assert rows[0][0].callback_data == "confirm:cadastro:123"
        assert rows[0][1].callback_data == "cancel:cadastro:123"

    def test_without_target_id(self):
        rows = confirm_keyboard("reset")
        assert rows[0][0].callback_data == "confirm:reset"
        assert rows[0][1].callback_data == "cancel:reset"


class TestParseCallbackData:
    """Tests for callback data parsing utility."""

    def test_simple_action(self):
        action, params = parse_callback_data("menu:proposicoes")
        assert action == "menu"
        assert params == ["proposicoes"]

    def test_vote_with_two_params(self):
        action, params = parse_callback_data("voto:1234:SIM")
        assert action == "voto"
        assert params == ["1234", "SIM"]

    def test_no_params(self):
        action, params = parse_callback_data("ajuda")
        assert action == "ajuda"
        assert params == []

    def test_three_params(self):
        action, params = parse_callback_data("confirm:cadastro:abc:def")
        assert action == "confirm"
        assert params == ["cadastro", "abc", "def"]


# ====================================================================== #
# Handlers                                                                #
# ====================================================================== #


def _make_message(**kwargs) -> IncomingMessage:
    """Helper to create an IncomingMessage with defaults."""
    defaults = {
        "chat_id": "12345",
        "user_id": "67890",
        "text": "/start",
        "channel": "telegram",
    }
    defaults.update(kwargs)
    return IncomingMessage(**defaults)


class TestHandleCommand:
    """Tests for command routing."""

    @pytest.mark.asyncio
    async def test_start_command(self):
        msg = _make_message(text="/start", first_name="Ana")
        result = await handle_command(msg)
        assert result["handled"] is True
        assert "Ana" in result["text"]
        assert result["buttons"] is not None

    @pytest.mark.asyncio
    async def test_ajuda_command(self):
        msg = _make_message(text="/ajuda")
        result = await handle_command(msg)
        assert result["handled"] is True
        assert "Comandos" in result["text"]

    @pytest.mark.asyncio
    async def test_menu_command(self):
        msg = _make_message(text="/menu")
        result = await handle_command(msg)
        assert result["handled"] is True
        assert result["buttons"] is not None

    @pytest.mark.asyncio
    async def test_reset_command(self):
        msg = _make_message(text="/reset")
        result = await handle_command(msg)
        assert result["handled"] is True
        assert result.get("reset_session") is True

    @pytest.mark.asyncio
    async def test_unknown_command_not_handled(self):
        msg = _make_message(text="/proposicoes saúde")
        result = await handle_command(msg)
        assert result["handled"] is False

    @pytest.mark.asyncio
    async def test_start_with_bot_name(self):
        msg = _make_message(text="/start@ParlamentarBot")
        result = await handle_command(msg)
        assert result["handled"] is True

    @pytest.mark.asyncio
    async def test_start_default_name(self):
        msg = _make_message(text="/start", first_name=None)
        result = await handle_command(msg)
        assert "eleitor(a)" in result["text"]


class TestHandleCallback:
    """Tests for callback query handling."""

    @pytest.mark.asyncio
    async def test_voto_callback(self):
        msg = _make_message(callback_data="voto:1234:SIM")
        result = await handle_callback(msg)
        assert result["to_agent"] is not None
        assert "1234" in result["to_agent"]
        assert "SIM" in result["to_agent"]
        assert result["callback_answer"] is not None

    @pytest.mark.asyncio
    async def test_votar_callback_shows_keyboard(self):
        msg = _make_message(callback_data="votar:999")
        result = await handle_callback(msg)
        assert result["buttons"] is not None
        assert result["to_agent"] is None
        assert "999" in result["text"]

    @pytest.mark.asyncio
    async def test_resultado_callback(self):
        msg = _make_message(callback_data="resultado:555")
        result = await handle_callback(msg)
        assert result["to_agent"] is not None
        assert "555" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_tramitacao_callback(self):
        msg = _make_message(callback_data="tramitacao:100")
        result = await handle_callback(msg)
        assert "100" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_analise_callback(self):
        msg = _make_message(callback_data="analise:200")
        result = await handle_callback(msg)
        assert "200" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_autores_callback(self):
        msg = _make_message(callback_data="autores:300")
        result = await handle_callback(msg)
        assert "300" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_despesas_callback(self):
        msg = _make_message(callback_data="despesas:50")
        result = await handle_callback(msg)
        assert "50" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_votacoes_dep_callback(self):
        msg = _make_message(callback_data="votacoes_dep:50")
        result = await handle_callback(msg)
        assert "50" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_menu_proposicoes_callback(self):
        msg = _make_message(callback_data="menu:proposicoes")
        result = await handle_callback(msg)
        assert result["to_agent"] is not None
        assert "proposições" in result["to_agent"].lower()

    @pytest.mark.asyncio
    async def test_menu_ajuda_callback(self):
        msg = _make_message(callback_data="menu:ajuda")
        result = await handle_callback(msg)
        assert result["text"] is not None
        assert result["to_agent"] is None

    @pytest.mark.asyncio
    async def test_page_callback(self):
        msg = _make_message(callback_data="page:proposicoes:3")
        result = await handle_callback(msg)
        assert "3" in result["to_agent"]

    @pytest.mark.asyncio
    async def test_confirm_callback(self):
        msg = _make_message(callback_data="confirm:cadastro:123")
        result = await handle_callback(msg)
        assert result["to_agent"] is not None
        assert result["callback_answer"] == "Confirmado!"

    @pytest.mark.asyncio
    async def test_cancel_callback(self):
        msg = _make_message(callback_data="cancel:cadastro")
        result = await handle_callback(msg)
        assert "cancelada" in (result.get("text") or "").lower()
        assert result["callback_answer"] == "Cancelado"

    @pytest.mark.asyncio
    async def test_unknown_callback(self):
        msg = _make_message(callback_data="unknown:data")
        result = await handle_callback(msg)
        assert result["to_agent"] is not None

    @pytest.mark.asyncio
    async def test_no_callback_data(self):
        msg = _make_message(callback_data=None)
        result = await handle_callback(msg)
        assert result["to_agent"] is None


# ====================================================================== #
# TelegramAdapter                                                         #
# ====================================================================== #


class TestTelegramAdapter:
    """Tests for the TelegramAdapter class."""

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_send_message(self, MockBot):
        mock_bot = AsyncMock()
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        await adapter.send_message("12345", "Hello!")

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == 12345
        assert call_kwargs.kwargs["text"] == "Hello!"

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_send_message_error(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Network error")
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        with pytest.raises(Exception, match="Network error"):
            await adapter.send_message("12345", "Hello!")

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_send_rich_message(self, MockBot):
        mock_bot = AsyncMock()
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        buttons = [[Button(text="A", callback_data="a"), Button(text="B", callback_data="b")]]
        await adapter.send_rich_message("12345", "Choose:", buttons)

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["reply_markup"] is not None

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_send_rich_message_error(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("API error")
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        buttons = [[Button(text="OK", callback_data="ok")]]
        with pytest.raises(Exception, match="API error"):
            await adapter.send_rich_message("12345", "Text", buttons)

    @pytest.mark.asyncio
    async def test_process_incoming_text_message(self):
        """Test parsing a regular text message from Telegram."""
        from channels.telegram.bot import TelegramAdapter

        # Use a real Bot object (no API calls needed for parsing)
        with patch("channels.telegram.bot.Bot") as MockBot:
            # The Bot must have a token attribute for Update.de_json
            real_bot = MagicMock()
            real_bot.token = "fake-token"
            MockBot.return_value = real_bot
            adapter = TelegramAdapter(token="fake-token")

        payload = {
            "update_id": 1,
            "message": {
                "message_id": 100,
                "date": 1700000000,
                "chat": {"id": 12345, "type": "private"},
                "from": {
                    "id": 67890,
                    "is_bot": False,
                    "first_name": "Ana",
                    "username": "ana_silva",
                },
                "text": "Olá!",
            },
        }

        # Use a real Bot for de_json parsing
        from telegram import Bot as RealBot
        adapter._bot = RealBot(token="fake-token")
        msg = await adapter.process_incoming(payload)

        assert msg is not None
        assert msg.chat_id == "12345"
        assert msg.user_id == "67890"
        assert msg.text == "Olá!"
        assert msg.username == "ana_silva"
        assert msg.first_name == "Ana"
        assert msg.channel == "telegram"
        assert msg.callback_data is None

    @pytest.mark.asyncio
    async def test_process_incoming_callback_query(self):
        """Test parsing a callback query (button press) from Telegram."""
        from channels.telegram.bot import TelegramAdapter
        from telegram import Bot as RealBot

        adapter = TelegramAdapter.__new__(TelegramAdapter)
        adapter._token = "fake-token"
        adapter._bot = RealBot(token="fake-token")

        payload = {
            "update_id": 2,
            "callback_query": {
                "id": "cb123",
                "data": "voto:1234:SIM",
                "from": {
                    "id": 67890,
                    "is_bot": False,
                    "first_name": "Ana",
                },
                "message": {
                    "message_id": 101,
                    "date": 1700000000,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Old message",
                },
                "chat_instance": "abc",
            },
        }

        msg = await adapter.process_incoming(payload)
        assert msg is not None
        assert msg.chat_id == "12345"
        assert msg.callback_data == "voto:1234:SIM"
        assert msg.text == "voto:1234:SIM"

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_process_incoming_ignores_non_text(self, MockBot):
        mock_bot = MagicMock()
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")

        # Photo message without text
        payload = {
            "update_id": 3,
            "message": {
                "message_id": 102,
                "date": 1700000000,
                "chat": {"id": 12345, "type": "private"},
                "from": {"id": 67890, "is_bot": False, "first_name": "X"},
                "photo": [{"file_id": "abc", "width": 100, "height": 100}],
            },
        }

        msg = await adapter.process_incoming(payload)
        assert msg is None

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_process_incoming_invalid_payload(self, MockBot):
        mock_bot = MagicMock()
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        msg = await adapter.process_incoming({"update_id": 99})
        assert msg is None

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_setup_webhook(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.set_webhook.return_value = True
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        result = await adapter.setup_webhook("https://example.com/webhook")
        assert result is True
        mock_bot.set_webhook.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_setup_webhook_failure(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.set_webhook.side_effect = Exception("Bad request")
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        result = await adapter.setup_webhook("https://example.com/webhook")
        assert result is False

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_answer_callback(self, MockBot):
        mock_bot = AsyncMock()
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        await adapter.answer_callback("cb123", "OK!")

        mock_bot.answer_callback_query.assert_awaited_once_with(
            callback_query_id="cb123",
            text="OK!",
        )

    @pytest.mark.asyncio
    @patch("channels.telegram.bot.Bot")
    async def test_answer_callback_error(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.answer_callback_query.side_effect = Exception("err")
        MockBot.return_value = mock_bot

        from channels.telegram.bot import TelegramAdapter

        adapter = TelegramAdapter(token="fake-token")
        # Should not raise
        await adapter.answer_callback("cb123", "OK!")


# ====================================================================== #
# Webhook endpoint                                                        #
# ====================================================================== #


class TestTelegramWebhook:
    """Tests for the Telegram webhook FastAPI endpoint."""

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook._run_agent", new_callable=AsyncMock)
    @patch("channels.telegram.webhook.get_adapter")
    async def test_text_message_routed_to_agent(self, mock_get_adapter, mock_run_agent):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="O que é o PL 100/2024?",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter
        mock_run_agent.return_value = "O PL 100/2024 dispõe sobre..."

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={
                    "update_id": 1,
                    "message": {
                        "message_id": 100,
                        "date": 1700000000,
                        "chat": {"id": 12345, "type": "private"},
                        "from": {"id": 67890, "is_bot": False, "first_name": "Test"},
                        "text": "O que é o PL 100/2024?",
                    },
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"
        mock_run_agent.assert_awaited_once()
        mock_adapter.send_message.assert_awaited()

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook.get_adapter")
    async def test_start_command_handled_directly(self, mock_get_adapter):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="/start",
            first_name="Ana",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={
                    "update_id": 1,
                    "message": {
                        "message_id": 100,
                        "date": 1700000000,
                        "chat": {"id": 12345, "type": "private"},
                        "from": {"id": 67890, "is_bot": False, "first_name": "Ana"},
                        "text": "/start",
                    },
                },
            )

        assert resp.status_code == 200
        # /start is handled directly — send_rich_message for the menu
        mock_adapter.send_rich_message.assert_awaited()

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook.settings")
    @patch("channels.telegram.webhook.get_adapter")
    async def test_invalid_secret_returns_403(self, mock_get_adapter, mock_settings):
        mock_settings.telegram_webhook_secret = "correct-secret"
        mock_settings.telegram_bot_token = "fake-token"

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook.get_adapter")
    async def test_ignored_update_returns_ignored(self, mock_get_adapter):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = None
        mock_get_adapter.return_value = mock_adapter

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={"update_id": 99},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook._run_agent", new_callable=AsyncMock)
    @patch("channels.telegram.webhook.get_adapter")
    async def test_callback_query_handled(self, mock_get_adapter, mock_run_agent):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="voto:1234:SIM",
            callback_data="voto:1234:SIM",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter
        mock_run_agent.return_value = "Voto registrado!"

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={
                    "update_id": 2,
                    "callback_query": {
                        "id": "cb123",
                        "data": "voto:1234:SIM",
                        "from": {"id": 67890, "is_bot": False, "first_name": "T"},
                        "message": {
                            "message_id": 101,
                            "date": 1700000000,
                            "chat": {"id": 12345, "type": "private"},
                            "text": "Old",
                        },
                        "chat_instance": "abc",
                    },
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"
        mock_run_agent.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook._run_agent", new_callable=AsyncMock)
    @patch("channels.telegram.webhook.get_adapter")
    async def test_agent_error_sends_error_message(self, mock_get_adapter, mock_run_agent):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="teste",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter
        mock_run_agent.side_effect = Exception("Agent error")

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhook/telegram",
                json={
                    "update_id": 3,
                    "message": {
                        "message_id": 102,
                        "date": 1700000000,
                        "chat": {"id": 12345, "type": "private"},
                        "from": {"id": 67890, "is_bot": False, "first_name": "X"},
                        "text": "teste",
                    },
                },
            )

        assert resp.status_code == 200
        # Error message sent to user
        assert mock_adapter.send_message.await_count >= 1

    @pytest.mark.asyncio
    @patch("channels.telegram.webhook._run_agent", new_callable=AsyncMock)
    @patch("channels.telegram.webhook.get_adapter")
    async def test_reset_command_resets_session(self, mock_get_adapter, mock_run_agent):
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="/reset",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter

        from httpx import ASGITransport, AsyncClient
        from channels.telegram.webhook import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        with patch("agents.parlamentar.runner.reset_session", new_callable=AsyncMock) as mock_reset:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/webhook/telegram",
                    json={
                        "update_id": 4,
                        "message": {
                            "message_id": 103,
                            "date": 1700000000,
                            "chat": {"id": 12345, "type": "private"},
                            "from": {"id": 67890, "is_bot": False, "first_name": "X"},
                            "text": "/reset",
                        },
                    },
                )

            assert resp.status_code == 200
            # The rich message (with menu) should be sent
            mock_adapter.send_rich_message.assert_awaited()
            # reset_session should have been called
            mock_reset.assert_awaited_once()


# ====================================================================== #
# WhatsApp placeholder                                                    #
# ====================================================================== #


class TestWhatsAppPlaceholder:
    """Tests for WhatsApp placeholder adapter."""

    @pytest.mark.asyncio
    async def test_send_message_not_implemented(self):
        from channels.whatsapp.placeholder import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        with pytest.raises(NotImplementedError):
            await adapter.send_message("12345", "Hello")

    @pytest.mark.asyncio
    async def test_process_incoming_not_implemented(self):
        from channels.whatsapp.placeholder import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        with pytest.raises(NotImplementedError):
            await adapter.process_incoming({})

    @pytest.mark.asyncio
    async def test_setup_webhook_not_implemented(self):
        from channels.whatsapp.placeholder import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        with pytest.raises(NotImplementedError):
            await adapter.setup_webhook("https://example.com")


# ====================================================================== #
# ChannelAdapter ABC                                                      #
# ====================================================================== #


class TestChannelAdapterABC:
    """Tests for the abstract ChannelAdapter base class."""

    def test_cannot_instantiate_abstract(self):
        from channels.base import ChannelAdapter
        with pytest.raises(TypeError):
            ChannelAdapter()

    def test_incoming_message_defaults(self):
        msg = IncomingMessage(chat_id="1", user_id="2", text="hi")
        assert msg.channel == "unknown"
        assert msg.callback_data is None
        assert msg.raw_payload is None

    def test_button_dataclass(self):
        btn = Button(text="OK", callback_data="ok")
        assert btn.text == "OK"
        assert btn.callback_data == "ok"


class TestWebhookSecretValidation:
    """Tests for the webhook secret token validation function."""

    def test_no_expected_secret_allows_any(self):
        from channels.telegram.webhook import _validate_secret_token
        assert _validate_secret_token("anything", None) is True
        assert _validate_secret_token("anything", "") is True

    def test_valid_secret(self):
        from channels.telegram.webhook import _validate_secret_token
        assert _validate_secret_token("my-secret", "my-secret") is True

    def test_invalid_secret(self):
        from channels.telegram.webhook import _validate_secret_token
        assert _validate_secret_token("wrong", "correct") is False

    def test_missing_token(self):
        from channels.telegram.webhook import _validate_secret_token
        assert _validate_secret_token(None, "expected") is False
