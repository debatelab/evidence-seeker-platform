"""Fact-checking models for EvidenceSeeker integration."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeAlias
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.evidence_seeker import EvidenceSeeker
    from app.models.user import User

from app.core.config import settings

# Import enums from evidence-seeker library when embeddings are enabled.
# In tests/CI we disable embeddings to avoid pulling heavy torch deps.
if not settings.disable_embeddings:
    try:  # pragma: no cover - relies on optional evidence_seeker package
        from evidence_seeker.datamodels import ConfirmationLevel, StatementType
    except Exception:  # pragma: no cover - fall back if optional dep missing
        StatementType = None  # type: ignore[assignment]
        ConfirmationLevel = None  # type: ignore[assignment]
else:
    StatementType = None  # type: ignore[assignment]
    ConfirmationLevel = None  # type: ignore[assignment]

if StatementType is None or ConfirmationLevel is None:
    # Fallback definitions if library not available (e.g., during tests/migrations)
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
InterpretationType: TypeAlias = StatementType  # noqa: UP040


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid4
    )
    evidence_seeker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=False
    )
    submitted_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[FactCheckRunStatus] = mapped_column(
        Enum(FactCheckRunStatus, name="fact_check_run_status"),
        nullable=False,
        default=FactCheckRunStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    began_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    evidence_seeker: Mapped[EvidenceSeeker] = relationship(
        "EvidenceSeeker", back_populates="fact_check_runs"
    )
    submitter: Mapped[User] = relationship("User")
    results: Mapped[list[FactCheckResult]] = relationship(
        "FactCheckResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FactCheckRun(uuid={self.uuid}, status={self.status})>"


class FactCheckResult(Base):
    """Interpretation-level results for a fact-check run."""

    __tablename__ = "fact_check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fact_check_runs.id"), nullable=False
    )
    interpretation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    interpretation_text: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation_type: Mapped[InterpretationType] = mapped_column(
        Enum(
            InterpretationType,
            name="fact_check_interpretation_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    confirmation_level: Mapped[ConfirmationLevel | None] = mapped_column(
        Enum(
            ConfirmationLevel,
            name="fact_check_confirmation_level",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped[FactCheckRun] = relationship("FactCheckRun", back_populates="results")
    evidence: Mapped[list[FactCheckEvidence]] = relationship(
        "FactCheckEvidence",
        back_populates="result",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FactCheckResult(run_id={self.run_id}, interpretation={self.interpretation_index})>"


class FactCheckEvidence(Base):
    """Supporting evidence chunks returned by EvidenceSeeker."""

    __tablename__ = "fact_check_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fact_check_results.id"), nullable=False
    )

    library_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_uuid: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True
    )
    chunk_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    stance: Mapped[EvidenceStance] = mapped_column(
        Enum(EvidenceStance, name="fact_check_evidence_stance"),
        nullable=False,
        default=EvidenceStance.SUPPORTS,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    result: Mapped[FactCheckResult] = relationship(
        "FactCheckResult", back_populates="evidence"
    )
    document: Mapped[Document] = relationship("Document")

    def __repr__(self) -> str:
        return f"<FactCheckEvidence(result_id={self.result_id}, stance={self.stance})>"


def build_fact_check_run(
    *,
    evidence_seeker_id: int,
    statement: str,
    status: FactCheckRunStatus = FactCheckRunStatus.PENDING,
    submitted_by: int | None = None,
    is_public: bool = False,
) -> FactCheckRun:
    """Construct a FactCheckRun instance with explicit, type-checked parameters."""
    run = FactCheckRun()
    run.evidence_seeker_id = evidence_seeker_id
    run.statement = statement
    run.status = status
    run.submitted_by = submitted_by
    run.is_public = is_public
    return run
