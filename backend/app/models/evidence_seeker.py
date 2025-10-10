from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from uuid import uuid4


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
    creator = relationship("User")

    def __repr__(self) -> str:
        return f"<EvidenceSeeker(id={self.id}, title='{self.title}')>"
