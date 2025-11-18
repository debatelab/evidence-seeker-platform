from datetime import datetime
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


class APIKey(Base):
    """Encrypted API key storage for AI services"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    evidence_seeker_uuid = Column(
        UUID(as_uuid=True), ForeignKey("evidence_seekers.uuid"), nullable=False
    )

    # Encrypted key data
    encrypted_key = Column(Text, nullable=False)  # Fernet-encrypted API key
    key_hash = Column(String(64), nullable=False)  # SHA-256 hash for validation

    # Metadata
    provider = Column(String(50), nullable=False)  # e.g., "huggingface", "openai"
    name = Column(String(100), nullable=False)  # User-friendly name for the key
    description = Column(Text, nullable=True)

    # Status and timestamps
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    evidence_seeker = relationship(
        "EvidenceSeeker", back_populates="api_keys", foreign_keys=[evidence_seeker_id]
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, provider='{self.provider}', name='{self.name}', evidence_seeker_id={self.evidence_seeker_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.utcnow()  # type: ignore[return-value]

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)"""
        return bool(self.is_active) and not self.is_expired
