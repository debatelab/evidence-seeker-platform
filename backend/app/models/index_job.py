import enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    document_uuid = Column(UUID(as_uuid=True), nullable=True)
    job_type = Column(String(50), nullable=False)
    status = Column(
        Enum(IndexJobStatus, name="index_job_status"),
        nullable=False,
        default=IndexJobStatus.QUEUED,
    )
    payload = Column(JSONB, nullable=True)
    operation_id = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    evidence_seeker = relationship(
        "EvidenceSeeker", back_populates="index_jobs", foreign_keys=[evidence_seeker_id]
    )
    submitter = relationship("User")

    def __repr__(self) -> str:
        return f"<IndexJob(uuid={self.uuid}, status={self.status}, job_type={self.job_type})>"
