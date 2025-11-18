from __future__ import annotations

from typing import Any

from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.evidence_seeker_settings import (
    ConfigurationState,
    SetupMode,
)


class EvidenceSeeker(Base):
    """Evidence Seeker SQLAlchemy model"""

    __tablename__ = "evidence_seekers"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_public = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    documents = relationship(
        "Document",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
        foreign_keys="Document.evidence_seeker_id",  # Use integer foreign key for relationship
    )
    permissions = relationship(
        "Permission", back_populates="evidence_seeker", cascade="all, delete-orphan"
    )
    settings = relationship(
        "EvidenceSeekerSettings",
        back_populates="evidence_seeker",
        uselist=False,
        cascade="all, delete-orphan",
    )
    fact_check_runs = relationship(
        "FactCheckRun",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
    )
    index_jobs = relationship(
        "IndexJob",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
    )
    api_keys = relationship(
        "APIKey",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
        foreign_keys="APIKey.evidence_seeker_id",
    )
    creator = relationship("User")

    def __repr__(self) -> str:
        return f"<EvidenceSeeker(id={self.id}, title='{self.title}')>"

    @property
    def configuration_state(self) -> str | None:
        if self.settings is None:
            return None
        return getattr(self.settings, "configuration_state", None)

    @property
    def missing_requirements(self) -> list[Any]:
        if self.settings is None:
            return []
        value = getattr(self.settings, "missing_requirements", []) or []
        if isinstance(value, list):
            return value
        return []

    @property
    def configured_at(self):
        if self.settings is None:
            return None
        return getattr(self.settings, "configured_at", None)

    @property
    def setup_mode(self) -> str | None:
        if self.settings is None:
            return None
        return getattr(self.settings, "setup_mode", None)

    @property
    def document_skip_acknowledged(self) -> bool:
        if self.settings is None:
            return False
        return bool(getattr(self.settings, "document_skip_acknowledged", False))
