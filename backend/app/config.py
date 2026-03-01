"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings via Pydantic BaseSettings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://parlamentaria:parlamentaria@localhost:5432/parlamentaria"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Câmara
    camara_api_base_url: str = "https://dadosabertos.camara.leg.br/api/v2"
    camara_api_rate_limit: float = 1.0

    # Google ADK / LLM
    agent_model: str = "gemini-2.0-flash"
    google_api_key: str = ""
    google_cloud_project: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""

    # WhatsApp Business API
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_verify_token: str = ""
    whatsapp_api_base_url: str = "https://graph.facebook.com/v21.0"

    # Admin API
    admin_api_key: str = "change-me-random-64-chars"

    # Publicação
    rss_base_url: str = "https://parlamentaria.app/rss"
    rss_ttl_minutes: int = 15
    webhook_dispatch_timeout: int = 10
    webhook_max_retries: int = 3
    webhook_circuit_breaker_threshold: int = 5

    # App
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"


settings = Settings()
