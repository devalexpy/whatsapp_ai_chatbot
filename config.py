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

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.app_base_url}/auth/google/callback"


settings = Settings()
