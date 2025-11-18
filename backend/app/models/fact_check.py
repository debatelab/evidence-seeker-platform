"""Fact-checking models for EvidenceSeeker integration."""

import enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

# Import enums from evidence-seeker library
try:
    from evidence_seeker.datamodels import ConfirmationLevel, StatementType
except ImportError:
    # Fallback definitions if library not available (e.g., during migrations)
    class StatementType(str, enum.Enum):  # type: ignore[no-redef]
        DESCRIPTIVE = "descriptive"
        ASCRIPTIVE = "ascriptive"
        NORMATIVE = "normative"

    class ConfirmationLevel(str, enum.Enum):  # type: ignore[no-redef]
        STRONGLY_CONFIRMED = "strongly_confirmed"
        CONFIRMED = "confirmed"
        WEAKLY_CONFIRMED = "weakly_confirmed"
        INCONCLUSIVE_CONFIRMATION = "inconclusive_confirmation"
        WEAKLY_DISCONFIRMED = "weakly_disconfirmed"
        DISCONFIRMED = "disconfirmed"
        STRONGLY_DISCONFIRMED = "strongly_disconfirmed"


# Alias for backward compatibility in our codebase
InterpretationType = StatementType


class FactCheckRunStatus(str, enum.Enum):
    """Execution status of a fact-check job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EvidenceStance(str, enum.Enum):
    """Support signal for a specific evidence chunk."""

    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NEUTRAL = "NEUTRAL"


class FactCheckRun(Base):
    """Top-level execution record for EvidenceSeeker runs."""

    __tablename__ = "fact_check_runs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    statement = Column(Text, nullable=False)
    status = Column(
        Enum(FactCheckRunStatus, name="fact_check_run_status"),
        nullable=False,
        default=FactCheckRunStatus.PENDING,
    )
    error_message = Column(Text, nullable=True)
    operation_id = Column(String(64), nullable=True)

    config_snapshot = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    began_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    evidence_seeker = relationship("EvidenceSeeker", back_populates="fact_check_runs")
    submitter = relationship("User")
    results = relationship(
        "FactCheckResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FactCheckRun(uuid={self.uuid}, status={self.status})>"


class FactCheckResult(Base):
    """Interpretation-level results for a fact-check run."""

    __tablename__ = "fact_check_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("fact_check_runs.id"), nullable=False)
    interpretation_index = Column(Integer, nullable=False)
    interpretation_text = Column(Text, nullable=False)
    interpretation_type = Column(
        Enum(
            InterpretationType,
            name="fact_check_interpretation_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    confirmation_level = Column(
        Enum(
            ConfirmationLevel,
            name="fact_check_confirmation_level",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    confidence_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)

    run = relationship("FactCheckRun", back_populates="results")
    evidence = relationship(
        "FactCheckEvidence",
        back_populates="result",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FactCheckResult(run_id={self.run_id}, interpretation={self.interpretation_index})>"


class FactCheckEvidence(Base):
    """Supporting evidence chunks returned by EvidenceSeeker."""

    __tablename__ = "fact_check_evidence"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("fact_check_results.id"), nullable=False)

    library_node_id = Column(String(100), nullable=True)
    document_uuid = Column(UUID(as_uuid=True), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    chunk_label = Column(String(255), nullable=True)
    evidence_text = Column(Text, nullable=False)
    stance = Column(
        Enum(EvidenceStance, name="fact_check_evidence_stance"),
        nullable=False,
        default=EvidenceStance.SUPPORTS,
    )
    score = Column(Float, nullable=True)
    metadata_payload = Column("metadata", JSONB, nullable=True)

    result = relationship("FactCheckResult", back_populates="evidence")
    document = relationship("Document")

    def __repr__(self) -> str:
        return f"<FactCheckEvidence(result_id={self.result_id}, stance={self.stance})>"
