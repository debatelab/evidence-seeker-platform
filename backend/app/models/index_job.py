from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence_seeker import EvidenceSeeker
    from app.models.user import User


class IndexJobStatus(str, enum.Enum):
    """Lifecycle status for indexing jobs."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IndexJob(Base):
    """Tracks asynchronous document ingestion jobs."""

    __tablename__ = "index_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid4
    )
    evidence_seeker_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_seekers.id"), nullable=False
    )
    submitted_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    document_uuid: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[IndexJobStatus] = mapped_column(
        Enum(IndexJobStatus, name="index_job_status"),
        nullable=False,
        default=IndexJobStatus.QUEUED,
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    operation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    evidence_seeker: Mapped[EvidenceSeeker] = relationship(
        "EvidenceSeeker", back_populates="index_jobs", foreign_keys=[evidence_seeker_id]
    )
    submitter: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return f"<IndexJob(uuid={self.uuid}, status={self.status}, job_type={self.job_type})>"
