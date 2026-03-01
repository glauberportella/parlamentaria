"""Tests for app.config module."""

from unittest.mock import patch

import pytest

from app.config import Settings


class TestSettings:
    """Test Settings behavior."""

    def test_default_values(self):
        """Settings should have sensible defaults for development."""
        s = Settings()
        assert s.app_env == "development"
        assert s.app_debug is True
        assert s.log_level == "INFO"
        assert "parlamentaria" in s.database_url
        assert s.redis_url.startswith("redis://")
        assert s.camara_api_base_url.startswith("https://")

    def test_is_production_false_by_default(self):
        """is_production should return False in development."""
        s = Settings()
        assert s.is_production is False

    def test_is_production_true(self):
        """is_production should return True when app_env is production."""
        s = Settings(app_env="production")
        assert s.is_production is True

    def test_camara_api_defaults(self):
        """Câmara API settings should have defaults."""
        s = Settings()
        assert "dadosabertos.camara.leg.br" in s.camara_api_base_url
        assert s.camara_api_rate_limit == 1.0

    def test_admin_api_key_default(self):
        """Admin API key should have a default value."""
        s = Settings()
        assert s.admin_api_key == "change-me-random-64-chars"

    def test_rss_settings(self):
        """RSS settings should have defaults."""
        s = Settings()
        assert s.rss_ttl_minutes == 15
        assert s.rss_base_url.startswith("https://")

    def test_webhook_settings(self):
        """Webhook settings should have defaults."""
        s = Settings()
        assert s.webhook_dispatch_timeout == 10
        assert s.webhook_max_retries == 3
        assert s.webhook_circuit_breaker_threshold == 5

    def test_custom_values(self):
        """Settings should accept custom values."""
        s = Settings(
            database_url="postgresql+asyncpg://user:pass@host/db",
            redis_url="redis://custom:6380/1",
            app_env="staging",
            log_level="DEBUG",
        )
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db"
        assert s.redis_url == "redis://custom:6380/1"
        assert s.app_env == "staging"
        assert s.log_level == "DEBUG"
