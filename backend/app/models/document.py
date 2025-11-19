from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence_seeker import EvidenceSeeker


class Document(Base):
    """Document SQLAlchemy model"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Preserve user's original filename
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_seeker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    evidence_seeker_uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_seekers.uuid"), nullable=False
    )

    # EvidenceSeeker indexing metadata
    index_file_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    evidence_seeker: Mapped[EvidenceSeeker] = relationship(
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


def build_document(
    *,
    title: str,
    file_path: str,
    original_filename: str,
    file_size: int,
    mime_type: str,
    evidence_seeker_id: int,
    evidence_seeker_uuid: UUIDType | str,
    description: str | None = None,
    index_file_key: str | None = None,
) -> Document:
    """Construct a Document instance with explicit, type-checked parameters."""
    document = Document()
    document.title = title
    document.file_path = file_path
    document.original_filename = original_filename
    document.file_size = file_size
    document.mime_type = mime_type
    document.evidence_seeker_id = evidence_seeker_id
    if isinstance(evidence_seeker_uuid, UUIDType):
        document.evidence_seeker_uuid = evidence_seeker_uuid
    else:
        document.evidence_seeker_uuid = UUIDType(evidence_seeker_uuid)
    document.description = description
    document.index_file_key = index_file_key
    return document
