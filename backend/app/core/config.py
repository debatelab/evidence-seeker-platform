from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = (
        "postgresql://evidence_user:evidence_password@localhost:5432/evidence_seeker"
    )

    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    jwt_secret_key: str = "your-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # 1 hour in seconds

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

    # Application
    debug: bool = False
    project_name: str = "Evidence Seeker Platform"
    version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    # Logging
    log_level: str = "INFO"

    # File Upload Settings
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_extensions: list = [".pdf", ".txt"]

    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@evidence-seeker.com"
    email_from_name: str = "Evidence Seeker Platform"

    # Email templates
    email_templates_dir: str = "backend/app/templates/email"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


settings = get_settings()
