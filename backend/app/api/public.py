from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.evidence_seeker_config_service import (
    ConfigurationNotReadyError,
    evidence_seeker_config_service,
)
from app.core.evidence_seeker_pipeline import evidence_seeker_pipeline_manager
from app.models.document import Document
from app.models.evidence_seeker import EvidenceSeeker
from app.models.fact_check import (
    FactCheckResult,
    FactCheckRun,
    FactCheckRunStatus,
)
from app.schemas.fact_check import (
    FactCheckResultRead,
    FactCheckRunCreate,
    FactCheckRunDetail,
    FactCheckRunRead,
)
from app.schemas.public import (
    PaginatedPublicEvidenceSeekers,
    PublicDocumentRead,
    PublicEvidenceSeekerDetail,
    PublicEvidenceSeekerDetailResponse,
    PublicEvidenceSeekerSummary,
    PublicFactCheckRunDetailResponse,
    PublicFactCheckRunSummary,
    PublicFactCheckRunsResponse,
)

router = APIRouter()


def _build_summary(
    seeker: EvidenceSeeker,
    *,
    document_count: int,
    latest_fact_check_at: datetime | None,
) -> PublicEvidenceSeekerSummary:
    return PublicEvidenceSeekerSummary(
        uuid=seeker.uuid,
        title=seeker.title,
        description=seeker.description,
        logo_url=seeker.logo_url,
        published_at=seeker.published_at,
        document_count=document_count,
        latest_fact_check_at=latest_fact_check_at,
    )


def _fetch_counts(
    db: Session,
    seeker_ids: Sequence[int],
) -> tuple[dict[int, int], dict[int, datetime]]:
    if not seeker_ids:
        return {}, {}

    doc_counts = {
        row[0]: row[1]
        for row in db.execute(
            select(Document.evidence_seeker_id, func.count(Document.id))
            .where(Document.evidence_seeker_id.in_(seeker_ids))
            .group_by(Document.evidence_seeker_id)
        )
    }

    latest_fact_checks = {
        row[0]: row[1]
        for row in db.execute(
            select(
                FactCheckRun.evidence_seeker_id,
                func.max(FactCheckRun.completed_at),
            )
            .where(
                FactCheckRun.evidence_seeker_id.in_(seeker_ids),
                FactCheckRun.is_public.is_(True),
                FactCheckRun.status == FactCheckRunStatus.SUCCEEDED,
            )
            .group_by(FactCheckRun.evidence_seeker_id)
        )
        if row[1] is not None
    }

    return doc_counts, latest_fact_checks


@router.get(
    "/evidence-seekers",
    response_model=PaginatedPublicEvidenceSeekers,
)
def list_public_evidence_seekers(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> PaginatedPublicEvidenceSeekers:
    filters: list = [EvidenceSeeker.is_public.is_(True)]
    if search:
        filters.append(
            func.lower(EvidenceSeeker.title).like(f"%{search.lower()}%")
        )

    total = db.execute(
        select(func.count()).select_from(EvidenceSeeker).where(*filters)
    ).scalar_one()

    seekers = (
        db.execute(
            select(EvidenceSeeker)
            .where(*filters)
            .order_by(
                desc(func.coalesce(EvidenceSeeker.published_at, EvidenceSeeker.updated_at))
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    doc_counts, latest_fact_checks = _fetch_counts(db, [s.id for s in seekers])
    summaries = [
        _build_summary(
            seeker,
            document_count=doc_counts.get(seeker.id, 0),
            latest_fact_check_at=latest_fact_checks.get(seeker.id),
        )
        for seeker in seekers
    ]

    return PaginatedPublicEvidenceSeekers(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/evidence-seekers/{seeker_uuid}",
    response_model=PublicEvidenceSeekerDetailResponse,
)
def get_public_evidence_seeker(
    seeker_uuid: UUID,
    db: Session = Depends(get_db),
) -> PublicEvidenceSeekerDetailResponse:
    seeker = (
        db.execute(
            select(EvidenceSeeker).where(
                EvidenceSeeker.uuid == seeker_uuid,
                EvidenceSeeker.is_public.is_(True),
            )
        )
        .scalars()
        .first()
    )

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    documents = (
        db.execute(
            select(Document)
            .where(Document.evidence_seeker_id == seeker.id)
            .order_by(desc(Document.created_at))
        )
        .scalars()
        .all()
    )

    recent_runs = (
        db.execute(
            select(FactCheckRun)
            .where(
                FactCheckRun.evidence_seeker_id == seeker.id,
                FactCheckRun.is_public.is_(True),
                FactCheckRun.status == FactCheckRunStatus.SUCCEEDED,
            )
            .order_by(
                desc(func.coalesce(FactCheckRun.published_at, FactCheckRun.completed_at))
            )
            .limit(10)
        )
        .scalars()
        .all()
    )

    doc_models = [
        PublicDocumentRead(
            uuid=document.uuid,
            title=document.title,
            description=document.description,
            original_filename=document.original_filename,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        for document in documents
    ]

    latest_fact_check_at = seeker.published_at
    if recent_runs:
        latest = recent_runs[0].completed_at or recent_runs[0].published_at
        if latest:
            latest_fact_check_at = latest

    recent_fact_checks = [
        PublicFactCheckRunSummary(
            uuid=run.uuid,
            statement=run.statement,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            completed_at=run.completed_at,
            published_at=run.published_at,
            evidence_seeker_uuid=seeker.uuid,
            evidence_seeker_id=seeker.id,
            evidence_seeker_title=seeker.title,
        )
        for run in recent_runs
    ]

    detail = PublicEvidenceSeekerDetail(
        uuid=seeker.uuid,
        title=seeker.title,
        description=seeker.description,
        logo_url=seeker.logo_url,
        published_at=seeker.published_at,
        document_count=len(documents),
        latest_fact_check_at=latest_fact_check_at,
        created_at=seeker.created_at,
        updated_at=seeker.updated_at,
        is_public=True,
    )

    return PublicEvidenceSeekerDetailResponse(
        seeker=detail,
        documents=doc_models,
        recent_fact_checks=recent_fact_checks,
    )


@router.post(
    "/evidence-seekers/{seeker_uuid}/fact-checks",
    response_model=FactCheckRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_public_fact_check(
    seeker_uuid: UUID,
    request: FactCheckRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> FactCheckRun:
    seeker = (
        db.execute(
            select(EvidenceSeeker).where(
                EvidenceSeeker.uuid == seeker_uuid,
                EvidenceSeeker.is_public.is_(True),
            )
        )
        .scalars()
        .first()
    )

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    run = evidence_seeker_pipeline_manager.create_fact_check_run(
        db=db,
        seeker=seeker,
        statement=request.statement,
        user_id=None,
        overrides=request.overrides,
        public_run=True,
    )

    background_tasks.add_task(
        evidence_seeker_pipeline_manager.execute_fact_check_run,
        run_id=int(run.id),
        seeker_id=int(seeker.id),
    )

    return run


@router.get(
    "/fact-checks",
    response_model=PublicFactCheckRunsResponse,
)
def list_public_fact_checks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PublicFactCheckRunsResponse:
    filters = [
        FactCheckRun.is_public.is_(True),
        FactCheckRun.status == FactCheckRunStatus.SUCCEEDED,
    ]

    total = db.execute(
        select(func.count()).select_from(FactCheckRun).where(*filters)
    ).scalar_one()

    rows = db.execute(
        select(FactCheckRun, EvidenceSeeker)
        .join(EvidenceSeeker, EvidenceSeeker.id == FactCheckRun.evidence_seeker_id)
        .where(*filters, EvidenceSeeker.is_public.is_(True))
        .order_by(
            desc(func.coalesce(FactCheckRun.published_at, FactCheckRun.completed_at))
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        PublicFactCheckRunSummary(
            uuid=run.uuid,
            statement=run.statement,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            completed_at=run.completed_at,
            published_at=run.published_at,
            evidence_seeker_uuid=seeker.uuid,
            evidence_seeker_id=seeker.id,
            evidence_seeker_title=seeker.title,
        )
        for run, seeker in rows
    ]

    return PublicFactCheckRunsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/fact-checks/{run_uuid}",
    response_model=PublicFactCheckRunDetailResponse,
)
def get_public_fact_check(
    run_uuid: UUID,
    db: Session = Depends(get_db),
) -> PublicFactCheckRunDetailResponse:
    row = db.execute(
        select(FactCheckRun, EvidenceSeeker)
        .join(EvidenceSeeker, EvidenceSeeker.id == FactCheckRun.evidence_seeker_id)
        .where(
            FactCheckRun.uuid == run_uuid,
            FactCheckRun.is_public.is_(True),
            EvidenceSeeker.is_public.is_(True),
        )
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Fact check not found")

    run, seeker = row

    results = (
        db.query(FactCheckResult)
        .options(selectinload(FactCheckResult.evidence))
        .filter(FactCheckResult.run_id == run.id)
        .order_by(FactCheckResult.interpretation_index)
        .all()
    )

    for result in results:
        for evidence in result.evidence:
            metadata = evidence.metadata_payload
            if metadata is not None:
                if hasattr(metadata, "model_dump"):
                    evidence.metadata_payload = metadata.model_dump()
                elif hasattr(metadata, "dict"):
                    evidence.metadata_payload = metadata.dict()
                elif not isinstance(metadata, dict):
                    try:
                        evidence.metadata_payload = dict(metadata)
                    except (TypeError, ValueError):
                        evidence.metadata_payload = {}

    document_count = db.execute(
        select(func.count()).select_from(Document).where(Document.evidence_seeker_id == seeker.id)
    ).scalar_one()

    summary = _build_summary(
        seeker,
        document_count=document_count,
        latest_fact_check_at=run.completed_at,
    )

    return PublicFactCheckRunDetailResponse(
        run=run,
        seeker=summary,
        results=results,
    )
