from uuid import uuid4

from sqlalchemy import (
    BigInteger,
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

    # EvidenceSeeker indexing metadata
    index_file_key = Column(String(255), nullable=True)

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
