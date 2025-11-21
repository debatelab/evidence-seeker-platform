from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.document import Document
    from app.models.evidence_seeker_settings import EvidenceSeekerSettings
    from app.models.fact_check import FactCheckRun
    from app.models.index_job import IndexJob
    from app.models.permission import Permission
    from app.models.user import User


class EvidenceSeeker(Base):
    """Evidence Seeker SQLAlchemy model"""

    __tablename__ = "evidence_seekers"
    __allow_unmapped__ = True
    _onboarding_token: str | None

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid4
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
        foreign_keys="Document.evidence_seeker_id",  # Use integer foreign key for relationship
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission", back_populates="evidence_seeker", cascade="all, delete-orphan"
    )
    settings: Mapped[EvidenceSeekerSettings | None] = relationship(
        "EvidenceSeekerSettings",
        back_populates="evidence_seeker",
        uselist=False,
        cascade="all, delete-orphan",
    )
    fact_check_runs: Mapped[list[FactCheckRun]] = relationship(
        "FactCheckRun",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
    )
    index_jobs: Mapped[list[IndexJob]] = relationship(
        "IndexJob",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list[APIKey]] = relationship(
        "APIKey",
        back_populates="evidence_seeker",
        cascade="all, delete-orphan",
        foreign_keys="APIKey.evidence_seeker_id",
    )
    creator: Mapped[User] = relationship("User")

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
    def configured_at(self) -> datetime | None:
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

    @property
    def onboarding_token(self) -> str | None:
        return getattr(self, "_onboarding_token", None)

    @onboarding_token.setter
    def onboarding_token(self, value: str | None) -> None:
        self._onboarding_token = value


def build_evidence_seeker(
    *,
    title: str,
    created_by: int,
    description: str | None = None,
    logo_url: str | None = None,
    is_public: bool = False,
    language: str | None = None,
) -> EvidenceSeeker:
    """Construct an EvidenceSeeker with explicit, type-checked parameters."""
    seeker = EvidenceSeeker()
    seeker.title = title
    seeker.created_by = created_by
    seeker.description = description
    seeker.logo_url = logo_url
    seeker.is_public = is_public
    seeker.language = language
    return seeker
