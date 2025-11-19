from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence_seeker import EvidenceSeeker


class APIKey(Base):
    """Encrypted API key storage for AI services"""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid4
    )
    evidence_seeker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    evidence_seeker_uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_seekers.uuid"), nullable=False
    )

    # Encrypted key data
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Metadata
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status and timestamps
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    evidence_seeker: Mapped[EvidenceSeeker] = relationship(
        "EvidenceSeeker", back_populates="api_keys", foreign_keys=[evidence_seeker_id]
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, provider='{self.provider}', name='{self.name}', evidence_seeker_id={self.evidence_seeker_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.utcnow()

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)"""
        return bool(self.is_active) and not self.is_expired


def build_api_key(
    *,
    evidence_seeker_id: int,
    evidence_seeker_uuid: UUIDType | str,
    encrypted_key: str,
    key_hash: str,
    provider: str,
    name: str,
    description: str | None = None,
    is_active: bool = True,
) -> APIKey:
    """Construct an APIKey instance with explicit, type-checked parameters."""
    key = APIKey()
    key.evidence_seeker_id = evidence_seeker_id
    if isinstance(evidence_seeker_uuid, UUIDType):
        key.evidence_seeker_uuid = evidence_seeker_uuid
    else:
        key.evidence_seeker_uuid = UUIDType(evidence_seeker_uuid)
    key.encrypted_key = encrypted_key
    key.key_hash = key_hash
    key.provider = provider
    key.name = name
    key.description = description
    key.is_active = is_active
    return key
