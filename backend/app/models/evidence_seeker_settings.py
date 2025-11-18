from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Boolean,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


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

    id = Column(Integer, primary_key=True, index=True)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    huggingface_api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    embed_backend_type = Column(
        String(50), nullable=False, server_default="huggingface"
    )
    embed_base_url = Column(String(255), nullable=True)
    embed_bill_to = Column(String(100), nullable=True)
    trust_remote_code = Column(Boolean, nullable=True)

    default_model = Column(String(150), nullable=True)
    temperature = Column(Float, nullable=True)
    top_k = Column(Integer, nullable=True)
    rerank_k = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    language = Column(String(32), nullable=True)

    metadata_filters = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )  # enforced to include seeker id in service
    pipeline_overrides = Column(JSONB, nullable=True)

    setup_mode = Column(String(16), nullable=False, server_default=SetupMode.SIMPLE.value)
    configuration_state = Column(
        String(32),
        nullable=False,
        server_default=ConfigurationState.UNCONFIGURED.value,
    )
    configured_at = Column(DateTime, nullable=True)
    missing_requirements = Column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    document_skip_acknowledged = Column(
        Boolean, nullable=False, server_default="false"
    )

    onboarding_token_jti = Column(String(64), nullable=True)
    onboarding_token_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    onboarding_token_expires_at = Column(DateTime, nullable=True)

    last_validated_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    evidence_seeker = relationship(
        "EvidenceSeeker", back_populates="settings", foreign_keys=[evidence_seeker_id]
    )
    huggingface_api_key = relationship("APIKey")
    onboarding_token_owner = relationship(
        "User", foreign_keys=[onboarding_token_owner_id], lazy="joined"
    )
    updated_by_user = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return (
            f"<EvidenceSeekerSettings("
            f"evidence_seeker_id={self.evidence_seeker_id}, default_model={self.default_model})>"
        )

    def mark_configured(self) -> None:
        self.configuration_state = ConfigurationState.READY.value
        self.missing_requirements = []
        self.configured_at = datetime.utcnow()
