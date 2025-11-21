from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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
    log_module_levels: str = ""  # Comma-separated list of module:level pairs
    sqlalchemy_echo: bool = False  # Set to True to see all SQL queries

    # File Upload Settings
    upload_storage_path: str = Field(
        default="/app/uploads",
        validation_alias=AliasChoices("UPLOAD_STORAGE_PATH", "UPLOAD_DIR"),
    )
    max_file_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_extensions: list[str] = [".pdf", ".txt"]

    # Public fact-check safeguards
    public_run_rate_limit_requests: int = 3
    public_run_rate_limit_window_seconds: int = 60
    public_run_queue_limit_per_seeker: int = 10

    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@evidence-seeker.com"
    email_from_name: str = "Evidence Seeker Platform"

    # Email templates (relative to backend working dir)
    email_templates_dir: str = "app/templates/email"

    # Feature flags
    # When true, the embedding model and heavy libraries are not loaded. Used in tests/CI.
    disable_embeddings: bool = False
    # When false, skip Base.metadata.create_all on startup and rely on migrations.
    auto_create_schema: bool = True
    # Controls whether the simplified configuration flow and backend guards are enabled.
    enable_simple_config: bool = True

    # Initial admin bootstrap
    auto_bootstrap_initial_admin: bool = True
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None
    initial_admin_username: str | None = None

    # EvidenceSeeker integration
    evse_run_timeout_seconds: int = 900
    evse_max_concurrent_runs: int = 5
    evse_default_model: str = (
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    evse_default_backend: str = "huggingface"
    evse_default_embed_base_url: str | None = None
    evse_postgres_schema: str | None = None
    evse_postgres_table_prefix: str = "evse_"
    evse_require_bill_to: bool = False

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }

    def get_module_log_levels(self) -> dict[str, str]:
        """Parse LOG_MODULE_LEVELS into a dictionary.

        Example: "evidence_seeker:DEBUG,app.api:INFO" ->
                 {"evidence_seeker": "DEBUG", "app.api": "INFO"}
        """
        if not self.log_module_levels:
            return {}

        levels: dict[str, str] = {}
        for pair in self.log_module_levels.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            module, level = pair.split(":", 1)
            levels[module.strip()] = level.strip().upper()

        return levels

    @property
    def upload_storage_directory(self) -> Path:
        """Return the configured upload storage directory."""
        return Path(self.upload_storage_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


settings = get_settings()
