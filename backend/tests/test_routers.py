"""Tests for FastAPI routers (health, admin, webhooks)."""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from channels.base import IncomingMessage


class TestHealthRouter:
    """Test health check endpoints."""

    async def test_health_check(self, client: AsyncClient):
        """GET /health should return 200 with ok status."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestWebhookRouter:
    """Test webhook endpoints."""

    @patch("channels.telegram.webhook._run_agent", new_callable=AsyncMock)
    @patch("channels.telegram.webhook.get_adapter")
    async def test_telegram_webhook(self, mock_get_adapter, mock_run_agent, client: AsyncClient):
        """POST /webhook/telegram should accept a payload and process it."""
        mock_adapter = AsyncMock()
        mock_adapter.process_incoming.return_value = IncomingMessage(
            chat_id="12345",
            user_id="67890",
            text="/start",
            first_name="Test",
            channel="telegram",
        )
        mock_get_adapter.return_value = mock_adapter

        resp = await client.post(
            "/webhook/telegram",
            json={"update_id": 1, "message": {"text": "/start"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    async def test_whatsapp_webhook(self, client: AsyncClient):
        """POST /webhook/whatsapp should accept a payload."""
        resp = await client.post(
            "/webhook/whatsapp",
            json={"entry": [{"changes": []}]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestAdminRouter:
    """Test admin endpoints."""

    async def test_admin_proposicoes_without_key(self, client: AsyncClient):
        """GET /admin/proposicoes without API key should return 422 (missing header)."""
        resp = await client.get("/admin/proposicoes")
        assert resp.status_code == 422

    async def test_admin_proposicoes_with_invalid_key(self, client: AsyncClient):
        """GET /admin/proposicoes with wrong key should return 401."""
        resp = await client.get(
            "/admin/proposicoes",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    async def test_admin_proposicoes_with_valid_key(self, client: AsyncClient):
        """GET /admin/proposicoes with correct key should return 200."""
        from app.config import settings

        resp = await client.get(
            "/admin/proposicoes",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200

    async def test_admin_eleitores_with_valid_key(self, client: AsyncClient):
        """GET /admin/eleitores with correct key should return 200."""
        from app.config import settings

        resp = await client.get(
            "/admin/eleitores",
            headers={"X-API-Key": settings.admin_api_key},
        )
        assert resp.status_code == 200

    async def test_admin_eleitores_unauthorized(self, client: AsyncClient):
        """GET /admin/eleitores without key should return 422."""
        resp = await client.get("/admin/eleitores")
        assert resp.status_code == 422


class TestExceptionHandlers:
    """Test custom exception handlers in main.py."""

    async def test_app_exception_handler(self, client: AsyncClient):
        """AppException should return JSON with detail."""
        # The admin route with wrong key raises UnauthorizedException
        resp = await client.get(
            "/admin/proposicoes",
            headers={"X-API-Key": "bad"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "detail" in data

    async def test_not_found_route(self, client: AsyncClient):
        """Non-existent route should return 404."""
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404


class TestMetaWebhookRouter:
    """Test Meta data-deletion callback endpoint."""

    async def test_meta_data_deletion_missing_params(self, client: AsyncClient):
        """POST without signed_request should return 400."""
        resp = await client.post(
            "/webhook/meta/data-deletion",
            data={},
        )
        assert resp.status_code == 400

    @patch("app.routers.meta_webhook.settings")
    async def test_meta_data_deletion_invalid_signature(self, mock_settings, client: AsyncClient):
        """POST with invalid signed_request should return 403."""
        mock_settings.meta_app_secret = "test-secret-123"
        resp = await client.post(
            "/webhook/meta/data-deletion",
            data={"signed_request": "invalid.payload"},
        )
        assert resp.status_code == 403

    @patch("app.routers.meta_webhook.settings")
    async def test_meta_data_deletion_valid_request(self, mock_settings, client: AsyncClient):
        """POST with valid signed_request should return 200 with confirmation."""
        import base64
        import hashlib
        import hmac
        import json

        app_secret = "test-secret-for-meta"
        mock_settings.meta_app_secret = app_secret

        # Build a valid signed_request
        payload = json.dumps({"user_id": "999999", "algorithm": "HMAC-SHA256"})
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        sig = hmac.new(
            app_secret.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        signed_request = f"{sig_b64}.{payload_b64}"

        resp = await client.post(
            "/webhook/meta/data-deletion",
            data={"signed_request": signed_request},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmation_code" in data
        assert "url" in data
        assert "exclusao-de-dados" in data["url"]

    @patch("app.routers.meta_webhook.settings")
    async def test_meta_data_deletion_deletes_existing_user(
        self, mock_settings, client: AsyncClient, db_session
    ):
        """Valid request should delete an existing voter with that chat_id."""
        import base64
        import hashlib
        import hmac
        import json
        from app.domain.eleitor import Eleitor

        app_secret = "test-secret-delete"
        mock_settings.meta_app_secret = app_secret

        # Create an eleitor with chat_id matching the Meta user_id
        eleitor = Eleitor(
            nome="Test User", email="test@meta.com", uf="SP",
            chat_id="meta_user_42", channel="whatsapp",
        )
        db_session.add(eleitor)
        await db_session.flush()

        payload = json.dumps({"user_id": "meta_user_42", "algorithm": "HMAC-SHA256"})
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        sig = hmac.new(
            app_secret.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        signed_request = f"{sig_b64}.{payload_b64}"

        resp = await client.post(
            "/webhook/meta/data-deletion",
            data={"signed_request": signed_request},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmation_code" in data
