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
    redis_url: str = "redis://:parlamentaria@localhost:6379/0"

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

    # RAG / Embeddings
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 3072
    rag_similarity_threshold: float = 0.3
    rag_max_results: int = 10

    # Engagement Digests
    digest_max_daily_notifications: int = 3
    digest_weekly_day: int = 0  # 0=Monday, 6=Sunday
    digest_weekly_hour: int = 9
    digest_daily_hour: int = 8
    digest_daily_minute: int = 30
    digest_batch_size: int = 50

    # Demo mode (development only — bypasses email auth)
    demo_mode: bool = False
    demo_user_email: str = "demo@parlamentaria.app"
    demo_user_nome: str = "Deputado(a) Demo"
    demo_deputado_id: int | None = None

    # CORS
    cors_extra_origins: str = ""  # Comma-separated additional CORS origins

    # Dashboard Parlamentar — Auth & JWT
    dashboard_url: str = "http://localhost:3000"

    # Painel do Cidadão (site público)
    cidadao_site_url: str = "http://localhost:3001"
    jwt_secret_key: str = "change-me-jwt-secret-key-64-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    magic_link_expire_minutes: int = 15
    magic_link_base_url: str = "http://localhost:3000/login/verify"

    # Resend (email for Magic Link)
    resend_api_key: str = ""
    email_from: str = "Parlamentaria <noreply@parlamentaria.app>"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"


settings = Settings()
