"""
Configuration settings for LOKAHOME API.
Uses Pydantic Settings for environment variable management.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_separated(value: str | list[str], default: list[str]) -> list[str]:
    """Parse comma-separated string into list."""
    if isinstance(value, list):
        return value
    if not value or not value.strip():
        return default
    return [item.strip() for item in value.split(",")]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "LOKAHOME API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API de location immobilière pour le Bénin"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Super Admin (créé automatiquement au démarrage)
    SUPERADMIN_EMAIL: str = "admin@lokahome.bj"
    SUPERADMIN_PASSWORD: str = "Admin@2024!"
    SUPERADMIN_FIRST_NAME: str = "Super"
    SUPERADMIN_LAST_NAME: str = "Admin"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 10000
    #PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False

    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://lokahome:lokahome@localhost:5432/lokahome"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")
    REDIS_CACHE_EXPIRE: int = 3600  # 1 hour

    # JWT Authentication
    SECRET_KEY: str = Field(default="your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - stored as strings, parsed as lists via computed_field
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        alias="CORS_ORIGINS",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS_STR: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS_STR: str = Field(default="*", alias="CORS_ALLOW_HEADERS")

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_TYPES_STR: str = Field(
        default="image/jpeg,image/png,image/webp",
        alias="ALLOWED_IMAGE_TYPES",
    )

    @computed_field
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return parse_comma_separated(
            self.CORS_ORIGINS_STR, ["http://localhost:3000", "http://localhost:8080"]
        )

    @computed_field
    @property
    def CORS_ALLOW_METHODS(self) -> list[str]:
        """Parse CORS methods from comma-separated string."""
        return parse_comma_separated(self.CORS_ALLOW_METHODS_STR, ["*"])

    @computed_field
    @property
    def CORS_ALLOW_HEADERS(self) -> list[str]:
        """Parse CORS headers from comma-separated string."""
        return parse_comma_separated(self.CORS_ALLOW_HEADERS_STR, ["*"])

    @computed_field
    @property
    def ALLOWED_IMAGE_TYPES(self) -> list[str]:
        """Parse allowed image types from comma-separated string."""
        return parse_comma_separated(
            self.ALLOWED_IMAGE_TYPES_STR, ["image/jpeg", "image/png", "image/webp"]
        )

    # AWS S3 / MinIO
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "lokahome"
    S3_REGION: str = "us-east-1"

    # FedaPay
    FEDAPAY_API_KEY: str = ""
    FEDAPAY_SECRET_KEY: str = ""
    FEDAPAY_ENVIRONMENT: Literal["sandbox", "live"] = "sandbox"
    FEDAPAY_WEBHOOK_SECRET: str = ""

    # Stripe
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Email (SMTP)
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@lokahome.bj"
    MAIL_FROM_NAME: str = "LOKAHOME"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # Twilio SMS
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    @property
    def database_url_sync(self) -> str:
        """Return synchronous database URL for Alembic."""
        return str(self.DATABASE_URL).replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
