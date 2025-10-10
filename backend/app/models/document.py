from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
    BigInteger,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from uuid import uuid4
import enum


class EmbeddingStatus(enum.Enum):
    """Status of document embedding generation"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    """Document SQLAlchemy model"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(
        String(255), nullable=False
    )  # Preserve user's original filename
    file_size = Column(BigInteger, nullable=False)  # File size in bytes
    mime_type = Column(String(100), nullable=False)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    evidence_seeker_uuid = Column(
        UUID(as_uuid=True), ForeignKey("evidence_seekers.uuid"), nullable=False
    )

    # Embedding-related fields
    embedding_status = Column(  # type: ignore[var-annotated]
        Enum(EmbeddingStatus), default=EmbeddingStatus.PENDING, nullable=False
    )
    embedding_generated_at = Column(DateTime, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    embedding_dimensions = Column(Integer, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    evidence_seeker = relationship(
        "EvidenceSeeker",
        back_populates="documents",
        foreign_keys=[evidence_seeker_id],  # Use integer foreign key for relationship
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', file_path='{self.file_path}')>"

    @staticmethod
    def get_mime_type_from_filename(filename: str) -> str:
        """Determine mime type from file extension"""
        if not filename:
            return "application/octet-stream"

        filename = filename.lower()
        if filename.endswith(".pdf"):
            return "application/pdf"
        elif filename.endswith(".txt"):
            return "text/plain"
        else:
            return "application/octet-stream"
