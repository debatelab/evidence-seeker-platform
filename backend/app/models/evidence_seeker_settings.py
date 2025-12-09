from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.api_key import APIKey

if TYPE_CHECKING:
    from app.models.evidence_seeker import EvidenceSeeker
    from app.models.user import User


class SetupMode(str, Enum):
    SIMPLE = "SIMPLE"
    EXPERT = "EXPERT"


class ConfigurationState(str, Enum):
    UNCONFIGURED = "UNCONFIGURED"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    MISSING_DOCUMENTS = "MISSING_DOCUMENTS"
    READY = "READY"
    ERROR = "ERROR"


class EvidenceSeekerSettings(Base):
    """Runtime configuration for EvidenceSeeker pipelines."""

    __tablename__ = "evidence_seeker_settings"
    __table_args__ = (
        UniqueConstraint(
            "evidence_seeker_id", name="uq_evidence_seeker_settings_seeker"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evidence_seeker_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_seekers.id"), nullable=False
    )
    huggingface_api_key_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("api_keys.id"), nullable=True
    )
    embed_backend_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="huggingface_inference_api"
    )
    embed_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embed_bill_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trust_remote_code: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    default_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rerank_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)

    metadata_filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )  # enforced to include seeker id in service
    pipeline_overrides: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    setup_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=SetupMode.SIMPLE.value
    )
    configuration_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ConfigurationState.UNCONFIGURED.value,
    )
    configured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    missing_requirements: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    document_skip_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    onboarding_token_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    onboarding_token_owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    onboarding_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    evidence_seeker: Mapped[EvidenceSeeker] = relationship(
        "EvidenceSeeker", back_populates="settings", foreign_keys=[evidence_seeker_id]
    )
    huggingface_api_key: Mapped[APIKey | None] = relationship("APIKey")
    onboarding_token_owner: Mapped[User | None] = relationship(
        "User", foreign_keys=[onboarding_token_owner_id], lazy="joined"
    )
    updated_by_user: Mapped[User | None] = relationship(
        "User", foreign_keys=[updated_by]
    )

    def __repr__(self) -> str:
        return (
            f"<EvidenceSeekerSettings("
            f"evidence_seeker_id={self.evidence_seeker_id}, default_model={self.default_model})>"
        )

    def mark_configured(self) -> None:
        self.configuration_state = ConfigurationState.READY.value
        self.missing_requirements = []
        self.configured_at = datetime.utcnow()


def build_evidence_seeker_settings(
    *,
    evidence_seeker_id: int,
    huggingface_api_key_id: int | None = None,
    embed_backend_type: str = "huggingface_inference_api",
    metadata_filters: dict[str, Any] | None = None,
    setup_mode: str = SetupMode.SIMPLE.value,
    configuration_state: str = ConfigurationState.UNCONFIGURED.value,
    missing_requirements: list[str] | None = None,
    **overrides: Any,
) -> EvidenceSeekerSettings:
    """Construct EvidenceSeekerSettings with explicit parameters."""
    settings = EvidenceSeekerSettings()
    settings.evidence_seeker_id = evidence_seeker_id
    settings.huggingface_api_key_id = huggingface_api_key_id
    settings.embed_backend_type = embed_backend_type
    settings.metadata_filters = metadata_filters or {}
    settings.setup_mode = setup_mode
    settings.configuration_state = configuration_state
    settings.missing_requirements = missing_requirements or []
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings
