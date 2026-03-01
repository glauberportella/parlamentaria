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
