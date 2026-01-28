from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "WhatsApp AI Chatbot"
    app_base_url: str = "http://localhost:8000"
    log_level: str = "DEBUG"

    # Frontend URLs (comma-separated for multiple origins)
    frontend_url: str = "http://localhost:3000"
    allowed_redirect_origins: str = "http://localhost:3000,http://localhost:5173"

    # Session
    session_secret_key: str = "change-me-in-production"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # MongoDB
    mongo_uri: str = ""

    # LLM Configuration
    openai_api_key: str = ""
    # Chat model
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_temperature: float = 0.7
    # Embedding model
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # Upstash QStash (background tasks)
    qstash_token: str = ""
    qstash_current_signing_key: str = ""  # Current signing key para verificar webhooks
    qstash_next_signing_key: str = ""  # Next signing key (para rotación)
    qstash_url: str = ""  # URL de QStash (local dev o producción)

    qstash_delay_seconds: int = 2  # Delay antes de procesar embedding

    # MinIO / S3
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "whatsapp-ai-bot"
    minio_secure: bool = False
    minio_presigned_url_expiry: int = 300  # 5 minutos para upload
    minio_download_url_expiry: int = 3600  # 1 hora para download

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.app_base_url}/auth/google/callback"


settings = Settings()
