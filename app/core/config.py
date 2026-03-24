"""Application configuration"""

import logging
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_prefix="AUTH_SERVICE__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: str = "development"
    port: int = 8003

    # Database
    db_url: str = "sqlite:///data/auth.db"

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # JWT Settings
    jwt_issuer: str = "https://auth.codelab.local"
    jwt_audience: str = "codelab-api"
    access_token_lifetime: int = 900  # 15 minutes
    refresh_token_lifetime: int = 2592000  # 30 days

    # RSA Keys
    private_key_path: str = "/app/keys/private_key.pem"
    public_key_path: str = "/app/keys/public_key.pem"

    # Security
    master_key: str | None = None  # Default admin password (if None, will be auto-generated)
    enable_rate_limiting: bool = True  # Enable/disable rate limiting
    rate_limit_per_ip: int = 5  # requests per minute
    rate_limit_per_username: int = 10  # requests per hour
    brute_force_threshold: int = 5  # failed attempts
    brute_force_lockout_duration: int = 900  # 15 minutes in seconds

    # Registration
    registration_rate_limit: int = 10  # requests per minute for /api/v1/register
    require_email_confirmation: bool = True  # Require email confirmation after registration
    suggest_usernames: bool = True  # Suggest usernames when username is already taken
    audit_log_retention_days: int = 90  # Days to retain audit logs

    # Password Reset
    password_reset_request_limit: int = 3  # requests per hour per email
    password_reset_token_expiration_minutes: int = 30  # token TTL

    # SMTP Configuration for email
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@codelab.local"
    smtp_use_tls: bool = True
    smtp_timeout: int = 30  # seconds
    smtp_max_retries: int = 3
    send_welcome_email: bool = True
    send_password_reset_email: bool = True

    # Logging
    log_level: str = "DEBUG"

    # Version
    version: str = "0.1.0"

    @field_validator('master_key', mode='before')
    @classmethod
    def validate_master_key(cls, v):
        """Convert empty string to None"""
        if v == "" or v is None:
            return None
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"


# Create settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("auth-service")
