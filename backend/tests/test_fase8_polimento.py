"""Tests for Fase 8 — Polimento (security, monitoring, deploy, WhatsApp, eval).

Covers:
- Enhanced health check (API Câmara, status aggregation, uptime)
- Middleware (RequestId, SecurityHeaders)
- Rate limiting configuration
- WhatsApp adapter (send, receive, webhook verification)
- ADK Eval runner (loading, evaluation, reporting)
- Webhook endpoints (WhatsApp verify + message)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from channels.base import Button, IncomingMessage


# ====================================================================== #
# Health Check Detailed                                                   #
# ====================================================================== #


class TestHealthDetailed:
    """Tests for the enhanced /health/detailed endpoint."""

    async def test_health_basic_still_works(self, client: AsyncClient):
        """GET /health should still return simple ok."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("app.routers.health.async_session_factory")
    async def test_health_detailed_unhealthy_db(self, mock_factory, client: AsyncClient):
        """If DB is down, overall status should be unhealthy."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute.side_effect = Exception("Connection refused")
        mock_factory.return_value = mock_session

        resp = await client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("unhealthy", "degraded")
        assert "version" in data
        assert "uptime_seconds" in data

    async def test_health_detailed_has_fields(self, client: AsyncClient):
        """Health detailed should include version, environment, uptime_seconds."""
        resp = await client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "environment" in data
        assert "uptime_seconds" in data
        assert "checks" in data
        assert isinstance(data["uptime_seconds"], (int, float))


# ====================================================================== #
# Middleware                                                               #
# ====================================================================== #


class TestRequestIdMiddleware:
    """Tests for the RequestId middleware."""

    async def test_response_has_request_id_header(self, client: AsyncClient):
        """Every response should include X-Request-Id header."""
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers
        # Should be a valid UUID-like string
        assert len(resp.headers["x-request-id"]) == 36

    async def test_response_has_response_time_header(self, client: AsyncClient):
        """Every response should include X-Response-Time header."""
        resp = await client.get("/health")
        assert "x-response-time" in resp.headers
        assert resp.headers["x-response-time"].endswith("ms")

    async def test_each_request_gets_unique_id(self, client: AsyncClient):
        """Two consecutive requests should get different request IDs."""
        resp1 = await client.get("/health")
        resp2 = await client.get("/health")
        assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    async def test_has_x_content_type_options(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_has_x_frame_options(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    async def test_has_x_xss_protection(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("x-xss-protection") == "1; mode=block"

    async def test_has_referrer_policy(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_has_permissions_policy(self, client: AsyncClient):
        resp = await client.get("/health")
        policy = resp.headers.get("permissions-policy")
        assert "camera=()" in policy
        assert "microphone=()" in policy


# ====================================================================== #
# Rate Limiter Configuration                                              #
# ====================================================================== #


class TestRateLimiter:
    """Tests for rate limiter configuration."""

    def test_limiter_configured(self):
        """Limiter should be importable and have default limits."""
        from app.middleware import limiter

        assert limiter is not None
        assert limiter._default_limits is not None

    def test_limiter_uses_memory_storage(self):
        """Limiter storage URI should be memory:// for tests."""
        from app.middleware import limiter

        assert limiter._storage_uri == "memory://"


# ====================================================================== #
# WhatsApp Adapter                                                        #
# ====================================================================== #


class TestWhatsAppAdapter:
    """Tests for the WhatsApp Business API adapter."""

    def _make_adapter(self):
        """Create a WhatsApp adapter instance."""
        from channels.whatsapp.adapter import WhatsAppAdapter
        return WhatsAppAdapter()

    def test_adapter_init(self):
        """Adapter should initialize with correct base URL."""
        adapter = self._make_adapter()
        assert adapter._base_url is not None
        assert "graph.facebook.com" in adapter._base_url

    def test_adapter_headers(self):
        """Adapter should have authorization and content-type headers."""
        adapter = self._make_adapter()
        assert "Authorization" in adapter._headers
        assert "Content-Type" in adapter._headers
        assert adapter._headers["Content-Type"] == "application/json"

    @patch("channels.whatsapp.adapter.httpx.AsyncClient")
    async def test_send_message(self, mock_client_class):
        """send_message should POST text to WhatsApp API."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        adapter = self._make_adapter()
        await adapter.send_message("5511999999999", "Hello!")

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello!"

    @patch("channels.whatsapp.adapter.httpx.AsyncClient")
    async def test_send_rich_message_buttons(self, mock_client_class):
        """send_rich_message should POST interactive buttons to WhatsApp API."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.456"}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        adapter = self._make_adapter()
        buttons = [[
            Button(text="Sim", callback_data="vote:yes"),
            Button(text="Não", callback_data="vote:no"),
        ]]
        await adapter.send_rich_message("5511999999999", "Vote:", buttons)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "button"
        assert len(payload["interactive"]["action"]["buttons"]) == 2

    @patch("channels.whatsapp.adapter.httpx.AsyncClient")
    async def test_send_rich_message_max_3_buttons(self, mock_client_class):
        """WhatsApp supports max 3 buttons; extras should be truncated."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.789"}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        adapter = self._make_adapter()
        buttons = [[
            Button(text="A", callback_data="a"),
            Button(text="B", callback_data="b"),
            Button(text="C", callback_data="c"),
            Button(text="D", callback_data="d"),  # should be truncated
        ]]
        await adapter.send_rich_message("5511999999999", "Choose:", buttons)

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert len(payload["interactive"]["action"]["buttons"]) == 3

    async def test_process_incoming_text_message(self):
        """process_incoming should parse a text message payload."""
        adapter = self._make_adapter()
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5511999999999",
                            "type": "text",
                            "text": {"body": "Olá!"},
                        }],
                        "contacts": [{
                            "profile": {"name": "Maria"},
                        }],
                    },
                }],
            }],
        }
        msg = await adapter.process_incoming(payload)
        assert msg is not None
        assert msg.chat_id == "5511999999999"
        assert msg.text == "Olá!"
        assert msg.channel == "whatsapp"
        assert msg.first_name == "Maria"

    async def test_process_incoming_button_reply(self):
        """process_incoming should parse an interactive button reply."""
        adapter = self._make_adapter()
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5511888888888",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "vote:yes",
                                    "title": "Sim",
                                },
                            },
                        }],
                        "contacts": [{"profile": {"name": "João"}}],
                    },
                }],
            }],
        }
        msg = await adapter.process_incoming(payload)
        assert msg is not None
        assert msg.callback_data == "vote:yes"
        assert msg.text == "Sim"

    async def test_process_incoming_empty_payload(self):
        """process_incoming should return None for empty/invalid payloads."""
        adapter = self._make_adapter()
        assert await adapter.process_incoming({}) is None
        assert await adapter.process_incoming({"entry": []}) is None
        assert await adapter.process_incoming({"entry": [{"changes": []}]}) is None

    async def test_process_incoming_status_update_ignored(self):
        """Status updates (no messages) should be ignored."""
        adapter = self._make_adapter()
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "statuses": [{"id": "wamid.123", "status": "delivered"}],
                    },
                }],
            }],
        }
        assert await adapter.process_incoming(payload) is None

    async def test_process_incoming_unsupported_type(self):
        """Unsupported message types (image, audio) should return None."""
        adapter = self._make_adapter()
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5511777777777",
                            "type": "image",
                            "image": {"id": "img123"},
                        }],
                        "contacts": [{"profile": {"name": "Test"}}],
                    },
                }],
            }],
        }
        assert await adapter.process_incoming(payload) is None

    async def test_setup_webhook_unconfigured(self):
        """setup_webhook should return False when credentials are missing."""
        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_api_token = ""
            mock_settings.whatsapp_phone_number_id = ""
            mock_settings.whatsapp_api_base_url = "https://graph.facebook.com/v21.0"

            from channels.whatsapp.adapter import WhatsAppAdapter
            adapter = WhatsAppAdapter()
            result = await adapter.setup_webhook("https://example.com/webhook/whatsapp")
            assert result is False

    async def test_setup_webhook_configured(self):
        """setup_webhook should return True when credentials are set."""
        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_api_token = "test-token"
            mock_settings.whatsapp_phone_number_id = "12345"
            mock_settings.whatsapp_api_base_url = "https://graph.facebook.com/v21.0"

            from channels.whatsapp.adapter import WhatsAppAdapter
            adapter = WhatsAppAdapter()
            result = await adapter.setup_webhook("https://example.com/webhook/whatsapp")
            assert result is True


# ====================================================================== #
# WhatsApp Webhook Verification                                           #
# ====================================================================== #


class TestWhatsAppWebhookVerification:
    """Tests for WhatsApp webhook challenge/response verification."""

    def test_verify_challenge_success(self):
        """Valid token should return the challenge string."""
        from channels.whatsapp.adapter import verify_webhook_challenge

        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_webhook_verify_token = "my-token"
            result = verify_webhook_challenge("subscribe", "my-token", "challenge123")
            assert result == "challenge123"

    def test_verify_challenge_wrong_token(self):
        """Wrong token should return None."""
        from channels.whatsapp.adapter import verify_webhook_challenge

        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_webhook_verify_token = "my-token"
            result = verify_webhook_challenge("subscribe", "wrong-token", "challenge123")
            assert result is None

    def test_verify_challenge_wrong_mode(self):
        """Wrong mode should return None."""
        from channels.whatsapp.adapter import verify_webhook_challenge

        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_webhook_verify_token = "my-token"
            result = verify_webhook_challenge("unsubscribe", "my-token", "challenge123")
            assert result is None

    def test_verify_challenge_none_values(self):
        """None values should return None."""
        from channels.whatsapp.adapter import verify_webhook_challenge

        with patch("channels.whatsapp.adapter.settings") as mock_settings:
            mock_settings.whatsapp_webhook_verify_token = "my-token"
            result = verify_webhook_challenge(None, None, None)
            assert result is None


class TestWhatsAppWebhookSignature:
    """Tests for HMAC-SHA256 webhook signature verification."""

    def test_verify_valid_signature(self):
        """Valid HMAC-SHA256 signature should pass."""
        import hmac
        import hashlib
        from channels.whatsapp.adapter import verify_webhook_signature

        secret = "test-secret"
        body = b'{"test": "payload"}'
        sig = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        assert verify_webhook_signature(body, sig, secret) is True

    def test_verify_invalid_signature(self):
        """Wrong signature should fail."""
        from channels.whatsapp.adapter import verify_webhook_signature

        assert verify_webhook_signature(b"body", "sha256=wrong", "secret") is False

    def test_verify_empty_signature(self):
        """Empty signature should fail."""
        from channels.whatsapp.adapter import verify_webhook_signature

        assert verify_webhook_signature(b"body", "", "secret") is False

    def test_verify_empty_secret(self):
        """Empty secret should fail."""
        from channels.whatsapp.adapter import verify_webhook_signature

        assert verify_webhook_signature(b"body", "sha256=abc", "") is False


# ====================================================================== #
# WhatsApp Webhook Endpoint                                               #
# ====================================================================== #


class TestWhatsAppWebhookEndpoint:
    """Tests for the /webhook/whatsapp HTTP endpoints."""

    async def test_whatsapp_webhook_post_empty(self, client: AsyncClient):
        """POST /webhook/whatsapp with no messages should return ignored."""
        resp = await client.post(
            "/webhook/whatsapp",
            json={"entry": [{"changes": [{"value": {}}]}]},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @patch("app.routers.webhooks._whatsapp_adapter")
    async def test_whatsapp_webhook_post_processes_message(
        self, mock_adapter, client: AsyncClient
    ):
        """POST /webhook/whatsapp with a valid message should process it."""
        mock_adapter.process_incoming = AsyncMock(return_value=IncomingMessage(
            chat_id="5511999999999",
            user_id="5511999999999",
            text="Olá!",
            channel="whatsapp",
        ))
        mock_adapter.send_message = AsyncMock()

        with patch("agents.parlamentar.runner.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Olá! Como posso ajudar?"

            resp = await client.post(
                "/webhook/whatsapp",
                json={"entry": [{"changes": [{"value": {"messages": [{"from": "5511999999999", "type": "text", "text": {"body": "Olá!"}}]}}]}]},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "processed"

    async def test_whatsapp_webhook_get_verify_wrong_token(self, client: AsyncClient):
        """GET /webhook/whatsapp with wrong token should return 403."""
        resp = await client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge123",
            },
        )
        assert resp.status_code == 403

    async def test_whatsapp_webhook_get_verify_correct_token(self, client: AsyncClient):
        """GET /webhook/whatsapp with correct token should return challenge."""
        from app.config import settings

        with patch.object(settings, "whatsapp_webhook_verify_token", "my-verify-token"):
            resp = await client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "my-verify-token",
                    "hub.challenge": "test-challenge-12345",
                },
            )
            assert resp.status_code == 200
            assert resp.text == "test-challenge-12345"


# ====================================================================== #
# ADK Eval Runner                                                         #
# ====================================================================== #


class TestEvalRunner:
    """Tests for the ADK evaluation runner."""

    def test_load_conversational_cases(self):
        """Should load conversational eval cases from JSON."""
        from agents.eval.eval_runner import load_eval_cases

        cases = load_eval_cases("conversational_eval.json")
        assert len(cases) > 0
        assert cases[0].name == "Saudação inicial"
        assert cases[0].initial_prompt == "Olá!"

    def test_load_proposicao_cases(self):
        """Should load proposicao eval cases from JSON."""
        from agents.eval.eval_runner import load_eval_cases

        cases = load_eval_cases("proposicao_eval.json")
        assert len(cases) == 5
        assert all(c.initial_prompt for c in cases)

    def test_load_votacao_cases(self):
        """Should load votacao eval cases from JSON."""
        from agents.eval.eval_runner import load_eval_cases

        cases = load_eval_cases("votacao_eval.json")
        assert len(cases) == 5
        assert cases[0].expected_tool_calls == ["registrar_voto"]

    def test_load_all_cases(self):
        """Should load all evaluation cases across all JSON datasets."""
        from agents.eval.eval_runner import load_all_eval_cases

        all_cases = load_all_eval_cases()
        # 8 conversational + 5 proposicao + 5 votacao = 18
        assert len(all_cases) == 18

    def test_check_response_contains_match(self):
        """check_response_contains should find matching substrings."""
        from agents.eval.eval_runner import check_response_contains

        assert check_response_contains("Olá! Sou o Parlamentaria.", ["ajud", "Parlamentar"])
        assert check_response_contains("Câmara dos Deputados", ["legislativ", "Câmara"])

    def test_check_response_contains_no_match(self):
        """check_response_contains should return False when no match."""
        from agents.eval.eval_runner import check_response_contains

        assert not check_response_contains("Hello World", ["legislativ", "Câmara"])

    def test_check_response_contains_empty_expected(self):
        """check_response_contains with empty expected should return True."""
        from agents.eval.eval_runner import check_response_contains

        assert check_response_contains("anything", [])

    def test_evaluate_case_response_match(self):
        """evaluate_case should pass when response contains expected substrings."""
        from agents.eval.eval_runner import EvalCase, evaluate_case

        case = EvalCase(
            name="Test",
            initial_prompt="Olá",
            expected_response_contains=["ajud", "Parlamentar"],
        )
        result = evaluate_case(case, "Olá! Sou o Parlamentaria. Em que posso ajudar?")
        assert result.passed is True
        assert result.response_matched is True

    def test_evaluate_case_response_no_match(self):
        """evaluate_case should fail when response doesn't match."""
        from agents.eval.eval_runner import EvalCase, evaluate_case

        case = EvalCase(
            name="Test",
            initial_prompt="Olá",
            expected_response_contains=["ajud", "Parlamentar"],
        )
        result = evaluate_case(case, "Error 500")
        assert result.passed is False
        assert result.response_matched is False

    def test_evaluate_case_agent_routing(self):
        """evaluate_case should check agent routing."""
        from agents.eval.eval_runner import EvalCase, evaluate_case

        case = EvalCase(
            name="Test",
            initial_prompt="Quero me cadastrar",
            expected_agent="EleitorAgent",
        )
        result = evaluate_case(case, "Ok", routed_agent="EleitorAgent")
        assert result.passed is True
        assert result.agent_matched is True

    def test_evaluate_case_wrong_agent(self):
        """evaluate_case should fail on wrong agent routing."""
        from agents.eval.eval_runner import EvalCase, evaluate_case

        case = EvalCase(
            name="Test",
            initial_prompt="Quero me cadastrar",
            expected_agent="EleitorAgent",
        )
        result = evaluate_case(case, "Ok", routed_agent="ProposicaoAgent")
        assert result.passed is False
        assert result.agent_matched is False

    def test_evaluate_case_tool_calls(self):
        """evaluate_case should check expected tool calls."""
        from agents.eval.eval_runner import EvalCase, evaluate_case

        case = EvalCase(
            name="Test",
            initial_prompt="Buscar proposições",
            expected_tool_calls=["buscar_proposicoes"],
        )
        result = evaluate_case(
            case, "Encontrei as proposições",
            called_tools=["buscar_proposicoes", "format_response"],
        )
        assert result.passed is True
        assert result.tools_matched is True

    def test_generate_report(self):
        """generate_eval_report should produce summary metrics."""
        from agents.eval.eval_runner import EvalCase, EvalResult, generate_eval_report

        results = [
            EvalResult(
                case=EvalCase(name="A", initial_prompt="a", tags=["tag1"]),
                passed=True,
                response_text="ok",
            ),
            EvalResult(
                case=EvalCase(name="B", initial_prompt="b", tags=["tag1", "tag2"]),
                passed=False,
                response_text="fail",
                errors=["Expected X got Y"],
            ),
        ]
        report = generate_eval_report(results)
        assert report["total"] == 2
        assert report["passed"] == 1
        assert report["failed"] == 1
        assert report["pass_rate"] == 50.0
        assert "tag1" in report["by_tag"]
        assert len(report["failures"]) == 1


# ====================================================================== #
# Config WhatsApp Settings                                                #
# ====================================================================== #


class TestWhatsAppConfig:
    """Tests for WhatsApp configuration settings."""

    def test_whatsapp_config_defaults(self):
        """WhatsApp config should have proper defaults."""
        from app.config import settings

        assert hasattr(settings, "whatsapp_api_token")
        assert hasattr(settings, "whatsapp_phone_number_id")
        assert hasattr(settings, "whatsapp_webhook_verify_token")
        assert hasattr(settings, "whatsapp_api_base_url")
        assert "graph.facebook.com" in settings.whatsapp_api_base_url

    def test_whatsapp_defaults_are_empty(self):
        """WhatsApp token defaults should be empty strings."""
        from app.config import settings

        assert settings.whatsapp_api_token == ""
        assert settings.whatsapp_phone_number_id == ""
        assert settings.whatsapp_webhook_verify_token == ""


# ====================================================================== #
# WhatsApp Adapter __init__ Module                                        #
# ====================================================================== #


class TestWhatsAppPackage:
    """Tests for the WhatsApp package structure."""

    def test_adapter_importable_from_package(self):
        """WhatsAppAdapter should be importable from channels.whatsapp."""
        from channels.whatsapp import WhatsAppAdapter
        assert WhatsAppAdapter is not None

    def test_adapter_is_channel_adapter(self):
        """WhatsAppAdapter should implement ChannelAdapter."""
        from channels.whatsapp import WhatsAppAdapter
        from channels.base import ChannelAdapter
        assert issubclass(WhatsAppAdapter, ChannelAdapter)

    def test_adapter_has_all_abstractmethods(self):
        """WhatsAppAdapter should implement all required abstract methods."""
        from channels.whatsapp import WhatsAppAdapter
        adapter = WhatsAppAdapter()
        assert hasattr(adapter, "send_message")
        assert hasattr(adapter, "send_rich_message")
        assert hasattr(adapter, "process_incoming")
        assert hasattr(adapter, "setup_webhook")
        assert hasattr(adapter, "answer_callback")


# ====================================================================== #
# Dockerfile and Docker Compose                                           #
# ====================================================================== #


class TestDockerConfig:
    """Tests for Dockerfile and docker-compose.yml correctness."""

    def test_dockerfile_is_multistage(self):
        """Dockerfile should have builder and runtime stages."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "AS builder" in content
        assert "AS runtime" in content
        assert "COPY --from=builder" in content

    def test_dockerfile_nonroot_user(self):
        """Dockerfile should run as non-root user."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "USER appuser" in content
        assert "groupadd" in content

    def test_dockerfile_healthcheck(self):
        """Dockerfile should have a HEALTHCHECK."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "HEALTHCHECK" in content

    def test_dockerfile_no_dev_deps(self):
        """Dockerfile runtime stage should not install dev dependencies."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        # The runtime stage should not have ".[dev]"
        # Builder installs only production deps
        assert '.[dev]' not in content

    def test_docker_compose_has_restart_policy(self):
        """docker-compose should have restart policies."""
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        assert "restart:" in content

    def test_docker_compose_has_redis_volume(self):
        """docker-compose should persist Redis data."""
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        assert "redisdata" in content
