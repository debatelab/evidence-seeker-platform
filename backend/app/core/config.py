from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


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
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

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

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


settings = get_settings()
