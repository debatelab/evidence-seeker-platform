import logging
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from ..core.auth import get_current_user
from ..core.config import settings
from ..core.config_service import config_service
from ..core.database import get_db
from ..core.evidence_seeker_config_service import (
    ConfigurationNotReadyError,
    evidence_seeker_config_service,
)
from ..core.evidence_seeker_index_service import evidence_seeker_index_service
from ..core.evidence_seeker_pipeline import evidence_seeker_pipeline_manager
from ..core.file_utils import delete_file
from ..core.onboarding_tokens import onboarding_token_service
from ..core.permissions import (
    check_evidence_seeker_permission,
    get_user_permissions,
)
from ..core.progress_tracker import progress_tracker
from ..models.document import Document
from ..models.evidence_seeker import EvidenceSeeker
from ..models.evidence_seeker_settings import EvidenceSeekerSettings, SetupMode
from ..models.fact_check import (
    FactCheckResult,
    FactCheckRun,
    FactCheckRunStatus,
)
from ..models.index_job import IndexJob
from ..models.permission import UserRole
from ..models.user import User
from ..schemas.evidence_seeker import (
    EvidenceSeekerCreate,
    EvidenceSeekerRead,
    EvidenceSeekerUpdate,
    InitialConfiguration,
)
from ..schemas.evidence_seeker_settings import (
    ConfigurationStatusRead,
    EvidenceSeekerSettingsRead,
    EvidenceSeekerSettingsUpdate,
    TestSettingsRequest,
)
from ..schemas.fact_check import (
    FactCheckRerunRequest,
    FactCheckResultRead,
    FactCheckRunCreate,
    FactCheckRunDetail,
    FactCheckRunRead,
)
from ..schemas.index_job import IndexJobRead
from ..schemas.search import (
    EvidenceSearchHit,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
)
from .documents import _process_index_update

router = APIRouter()
logger = logging.getLogger(__name__)


def _configuration_error_detail(exc: ConfigurationNotReadyError) -> dict[str, object]:
    payload = evidence_seeker_config_service.serialise_status(exc.status)
    payload.setdefault("message", "Evidence Seeker configuration incomplete")
    return payload


def _apply_initial_configuration(
    db: Session,
    seeker: EvidenceSeeker,
    initial_config: InitialConfiguration,
) -> None:
    """Create provider key and attach it to the seeker's settings."""
    try:
        api_key = config_service.create_api_key(
            evidence_seeker_id=int(seeker.id),
            provider="huggingface",
            name=initial_config.api_key_name,
            api_key=initial_config.api_key_value,
            description="Primary Hugging Face key",
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    setup_mode = SetupMode(initial_config.setup_mode)
    evidence_seeker_config_service.apply_initial_configuration(
        db=db,
        seeker=seeker,
        api_key_id=int(api_key.id),
        bill_to=initial_config.bill_to,
        setup_mode=setup_mode,
    )


try:  # pragma: no cover - optional dependency during tests
    from evidence_seeker import CheckedClaim
    from evidence_seeker.retrieval.document_retriever import DocumentRetriever
except ImportError:  # pragma: no cover
    CheckedClaim = None  # type: ignore[assignment]
    DocumentRetriever = None  # type: ignore[assignment]


def _ensure_admin(user_id: int, seeker: EvidenceSeeker, db: Session) -> None:
    if not check_evidence_seeker_permission(
        user_id, int(seeker.id), UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )


def get_evidence_seeker_by_identifier(
    identifier: int | str,
    db: Session,
    current_user_id: int,
) -> EvidenceSeeker:
    """Helper function to get Evidence Seeker by ID or UUID with permission check"""
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(identifier))
        result = db.execute(
            select(EvidenceSeeker)
            .options(selectinload(EvidenceSeeker.settings))
            .where(EvidenceSeeker.uuid == uuid_obj)
        )
        seeker = result.scalar_one_or_none()
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        result = db.execute(
            select(EvidenceSeeker)
            .options(selectinload(EvidenceSeeker.settings))
            .where(EvidenceSeeker.id == int(identifier))
        )
        seeker = result.scalar_one_or_none()

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check if user has read access to this evidence seeker
    if not check_evidence_seeker_permission(
        current_user_id, int(seeker.id), UserRole.EVSE_READER, db
    ):
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    return seeker


def get_accessible_evidence_seekers(user_id: int, db: Session) -> list[EvidenceSeeker]:
    """Get all evidence seekers accessible to a user based on permissions"""
    # Platform admins have access to all evidence seekers
    if check_evidence_seeker_permission(user_id, 0, UserRole.PLATFORM_ADMIN, db):
        result = db.execute(
            select(EvidenceSeeker).options(selectinload(EvidenceSeeker.settings))
        )
        return list(result.scalars().all())

    # Get user's permissions
    permissions = get_user_permissions(user_id, db)

    # Collect evidence seeker IDs the user has access to
    accessible_ids = set()
    for permission in permissions:
        accessible_ids.add(permission.evidence_seeker_id)

    # Also include evidence seekers created by the user or public ones
    result = db.execute(
        select(EvidenceSeeker)
        .options(selectinload(EvidenceSeeker.settings))
        .where((EvidenceSeeker.created_by == user_id) | EvidenceSeeker.is_public)
    )
    created_or_public = result.scalars().all()

    for seeker in created_or_public:
        accessible_ids.add(seeker.id)

    if accessible_ids:
        result = db.execute(
            select(EvidenceSeeker)
            .options(selectinload(EvidenceSeeker.settings))
            .where(EvidenceSeeker.id.in_(list(accessible_ids)))
        )
        return list(result.scalars().all())
    return []


@router.post("/", response_model=EvidenceSeekerRead)
def create_evidence_seeker(
    seeker: EvidenceSeekerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSeeker:
    """Create a new Evidence Seeker"""
    seeker_payload = seeker.model_dump(
        exclude={"initial_configuration"}, exclude_none=True
    )
    db_seeker = EvidenceSeeker(**seeker_payload, created_by=current_user.id)
    db.add(db_seeker)
    db.commit()
    db.refresh(db_seeker)

    if seeker.initial_configuration is not None:
        _apply_initial_configuration(db, db_seeker, seeker.initial_configuration)
        db.refresh(db_seeker)
    else:
        evidence_seeker_config_service.ensure_settings(db, db_seeker)

    settings_row = evidence_seeker_config_service.ensure_settings(db, db_seeker)
    onboarding_token = onboarding_token_service.issue_token(
        db=db,
        seeker=db_seeker,
        owner_user_id=int(current_user.id),
    )
    db.refresh(settings_row)
    db_seeker.onboarding_token = onboarding_token
    return db_seeker


@router.get("/", response_model=list[EvidenceSeekerRead])
def get_evidence_seekers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EvidenceSeeker]:
    """Get all Evidence Seekers accessible to the current user"""
    seekers = get_accessible_evidence_seekers(int(current_user.id), db)
    return seekers[skip : skip + limit]


@router.get("/{seeker_id}", response_model=EvidenceSeekerRead)
def get_evidence_seeker(
    seeker_id: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSeeker:
    """Get a specific Evidence Seeker by ID or UUID"""
    return get_evidence_seeker_by_identifier(seeker_id, db, int(current_user.id))


@router.get(
    "/{seeker_identifier}/status",
    response_model=ConfigurationStatusRead,
)
def get_configuration_status(
    seeker_identifier: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConfigurationStatusRead:
    """Return configuration status for readers and admins."""
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    status = evidence_seeker_config_service.get_configuration_status(db, seeker)
    payload = evidence_seeker_config_service.serialise_status(status)
    return ConfigurationStatusRead(**payload)


@router.post(
    "/{seeker_identifier}/onboarding/skip-documents",
    response_model=ConfigurationStatusRead,
)
def acknowledge_document_skip(
    seeker_identifier: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConfigurationStatusRead:
    """Record that the admin chose to defer document uploads."""
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    evidence_seeker_config_service.acknowledge_document_skip(
        db=db,
        seeker=seeker,
        acknowledged=True,
    )
    status = evidence_seeker_config_service.get_configuration_status(db, seeker)
    progress_tracker.record_event(
        "evse_onboarding_skip_documents",
        user_id=int(current_user.id),
        evidence_seeker_id=int(seeker.id),
    )
    return ConfigurationStatusRead(
        **evidence_seeker_config_service.serialise_status(status)
    )


@router.post(
    "/{seeker_identifier}/finish-onboarding",
    response_model=ConfigurationStatusRead,
)
def finish_onboarding(
    seeker_identifier: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConfigurationStatusRead:
    """Finalize onboarding by revoking the wizard token and returning status."""
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    settings_row = evidence_seeker_config_service.ensure_settings(db, seeker)
    onboarding_token_service.revoke_token(db, settings_row)
    status = evidence_seeker_config_service.get_configuration_status(db, seeker)
    return ConfigurationStatusRead(
        **evidence_seeker_config_service.serialise_status(status)
    )


@router.put("/{seeker_id}", response_model=EvidenceSeekerRead)
def update_evidence_seeker(
    seeker_id: int | str,
    seeker_update: EvidenceSeekerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSeeker:
    """Update an Evidence Seeker - requires admin permissions"""
    # Get the seeker first to check permissions
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(seeker_id))
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.uuid == uuid_obj)
        )
        seeker = result.scalar_one_or_none()
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.id == int(seeker_id))
        )
        seeker = result.scalar_one_or_none()

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check admin permissions
    if not check_evidence_seeker_permission(
        int(current_user.id), int(seeker.id), UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )

    updates = seeker_update.dict(exclude_unset=True)
    original_is_public = seeker.is_public
    for field, value in updates.items():
        setattr(seeker, field, value)

    if "is_public" in updates and updates["is_public"] != original_is_public:
        if updates["is_public"]:
            seeker.published_at = datetime.utcnow()
        else:
            seeker.published_at = None
            (
                db.query(FactCheckRun)
                .filter(
                    FactCheckRun.evidence_seeker_id == seeker.id,
                    FactCheckRun.is_public.is_(True),
                )
                .update(
                    {"is_public": False, "published_at": None},
                    synchronize_session=False,
                )
            )
    db.commit()
    db.refresh(seeker)
    return seeker


@router.delete("/{seeker_id}")
def delete_evidence_seeker(
    seeker_id: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete an Evidence Seeker - requires admin permissions"""
    # Get the seeker first to check permissions
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(seeker_id))
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.uuid == uuid_obj)
        )
        seeker = result.scalar_one_or_none()
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.id == int(seeker_id))
        )
        seeker = result.scalar_one_or_none()

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check admin permissions
    if not check_evidence_seeker_permission(
        int(current_user.id), int(seeker.id), UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )

    # Delete all associated documents and their files
    result = db.execute(
        select(Document).where(Document.evidence_seeker_id == seeker.id)
    )
    documents = result.scalars().all()

    for document in documents:
        # Delete the actual file from disk
        delete_file(document.file_path)
        # Delete document from database
        db.delete(document)

    # Delete the upload directory for this Evidence Seeker
    upload_dir = Path(settings.upload_dir) / str(seeker.id)
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
        except Exception as e:
            # Log error but don't prevent deletion
            print(f"Warning: Could not delete upload directory {upload_dir}: {e}")

    # Delete the Evidence Seeker
    db.delete(seeker)
    db.commit()
    return {"detail": "Evidence Seeker and all associated documents deleted"}


@router.get("/{seeker_identifier}/settings", response_model=EvidenceSeekerSettingsRead)
def get_evidence_seeker_settings(
    seeker_identifier: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSeekerSettings:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    settings_row = evidence_seeker_config_service.ensure_settings(db, seeker)
    evidence_seeker_config_service.get_configuration_status(db, seeker)
    db.refresh(settings_row)
    return settings_row


@router.put("/{seeker_identifier}/settings", response_model=EvidenceSeekerSettingsRead)
def update_evidence_seeker_settings(
    seeker_identifier: int | str,
    payload: EvidenceSeekerSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSeekerSettings:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    try:
        settings_row = evidence_seeker_config_service.upsert_settings(
            db=db,
            seeker=seeker,
            payload=payload.model_dump(exclude_unset=True),
            updated_by=int(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    evidence_seeker_pipeline_manager.invalidate(int(seeker.id))
    return settings_row


@router.post("/{seeker_identifier}/settings/test")
def test_evidence_seeker_settings(
    seeker_identifier: int | str,
    request: TestSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)

    if DocumentRetriever is None:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EvidenceSeeker library is not installed on the server",
        )

    overrides: dict[str, object] = {}
    if request.metadata_filters:
        overrides["metadata_filters"] = request.metadata_filters

    bundle = evidence_seeker_config_service.build_retrieval_bundle(
        db=db,
        seeker=seeker,
        overrides=overrides,
    )

    try:
        retriever = DocumentRetriever(config=bundle.config)
        filters = retriever.create_metadata_filters(bundle.metadata_filters)
    except Exception as exc:  # pragma: no cover - runtime failure path
        logger.exception("Failed to validate EvidenceSeeker settings")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration validation failed: {exc}",
        ) from exc

    return {
        "detail": "Configuration validated successfully",
        "metadataFilters": filters,
    }


@router.post(
    "/{seeker_identifier}/documents/reindex",
    response_model=IndexJobRead,
)
def reindex_documents(
    seeker_identifier: int | str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IndexJob:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_configuration_error_detail(exc),
        ) from exc

    documents = (
        db.query(Document).filter(Document.evidence_seeker_id == seeker.id).all()
    )
    if not documents:
        raise HTTPException(status_code=400, detail="No documents available to reindex")

    job = evidence_seeker_index_service.queue_update(
        db=db,
        seeker=seeker,
        user_id=int(current_user.id),
        documents=documents,
    )

    background_tasks.add_task(
        _process_index_update,
        job.id,
        [int(document.id) for document in documents],
    )

    return job


@router.get(
    "/{seeker_identifier}/index-jobs",
    response_model=list[IndexJobRead],
)
def list_index_jobs(
    seeker_identifier: int | str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IndexJob]:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)

    jobs = (
        db.query(IndexJob)
        .filter(IndexJob.evidence_seeker_id == seeker.id)
        .order_by(desc(IndexJob.created_at))
        .limit(100)
        .all()
    )
    return jobs


@router.post(
    "/{seeker_identifier}/search",
    response_model=EvidenceSearchResponse,
)
async def search_evidence(
    seeker_identifier: int | str,
    request: EvidenceSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceSearchResponse:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_configuration_error_detail(exc),
        ) from exc

    if DocumentRetriever is None or CheckedClaim is None:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EvidenceSeeker library is not installed on the server",
        )

    overrides: dict[str, object] = {}
    if request.top_k is not None:
        overrides["top_k"] = request.top_k
    if request.metadata_filters:
        overrides.setdefault("metadata_filters", {}).update(request.metadata_filters)
    if request.document_uuids:
        filters = overrides.setdefault("metadata_filters", {})
        filters["document_uuid"] = [str(uuid) for uuid in request.document_uuids]

    bundle = evidence_seeker_config_service.build_retrieval_bundle(
        db=db,
        seeker=seeker,
        overrides=overrides,
    )

    retriever = DocumentRetriever(config=bundle.config)
    metadata_filters = dict(bundle.metadata_filters)
    if request.metadata_filters:
        metadata_filters.update(request.metadata_filters)
    if request.document_uuids:
        metadata_filters["document_uuid"] = [
            str(uuid) for uuid in request.document_uuids
        ]

    retriever_filters = retriever.create_metadata_filters(metadata_filters)
    claim = CheckedClaim(text=request.query, uid="search-query")

    documents = await retriever.retrieve_documents(claim, retriever_filters)

    limit = request.top_k or len(documents)
    hits: list[EvidenceSearchHit] = []
    for doc in documents[:limit]:
        metadata = getattr(doc, "metadata", {}) or {}
        hits.append(
            EvidenceSearchHit(
                score=float(getattr(doc, "score", metadata.get("score", 0.0))),
                text=getattr(doc, "text", metadata.get("text", "")),
                document_uuid=metadata.get("document_uuid"),
                document_id=metadata.get("document_id"),
                metadata=metadata,
            )
        )

    return EvidenceSearchResponse(query=request.query, results=hits)


@router.get(
    "/{seeker_identifier}/runs",
    response_model=list[FactCheckRunRead],
)
def list_fact_check_runs(
    seeker_identifier: int | str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FactCheckRun]:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    # Readers can examine runs
    runs = (
        db.query(FactCheckRun)
        .filter(FactCheckRun.evidence_seeker_id == seeker.id)
        .order_by(desc(FactCheckRun.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return runs


@router.post(
    "/{seeker_identifier}/runs",
    response_model=FactCheckRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_fact_check_run(
    seeker_identifier: int | str,
    request: FactCheckRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FactCheckRun:
    """
    Start a fact-check run as a background task.

    Returns immediately with the run object in PENDING status.
    The actual fact-checking happens asynchronously in the background.
    Clients should poll the run status or subscribe to progress updates
    via the operation_id to track completion.
    """
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_configuration_error_detail(exc),
        ) from exc

    run = evidence_seeker_pipeline_manager.create_fact_check_run(
        db=db,
        seeker=seeker,
        statement=request.statement,
        user_id=int(current_user.id),
        overrides=request.overrides,
    )

    # Schedule the actual execution as a background task
    background_tasks.add_task(
        evidence_seeker_pipeline_manager.execute_fact_check_run,
        run_id=int(run.id),
        seeker_id=int(seeker.id),
    )

    return run


@router.get(
    "/{seeker_identifier}/runs/{run_uuid}",
    response_model=FactCheckRunDetail,
)
def get_fact_check_run(
    seeker_identifier: int | str,
    run_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FactCheckRun:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )

    run = (
        db.query(FactCheckRun)
        .filter(
            FactCheckRun.evidence_seeker_id == seeker.id, FactCheckRun.uuid == run_uuid
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Fact-check run not found")
    return run


@router.get(
    "/{seeker_identifier}/runs/{run_uuid}/results",
    response_model=list[FactCheckResultRead],
)
def get_fact_check_results(
    seeker_identifier: int | str,
    run_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FactCheckResult]:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )

    run = (
        db.query(FactCheckRun)
        .filter(
            FactCheckRun.evidence_seeker_id == seeker.id, FactCheckRun.uuid == run_uuid
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Fact-check run not found")

    results = (
        db.query(FactCheckResult)
        .options(selectinload(FactCheckResult.evidence))
        .filter(FactCheckResult.run_id == run.id)
        .order_by(FactCheckResult.interpretation_index)
        .all()
    )

    # Convert any MetaData objects to dicts in evidence metadata
    # Do this immediately after query to avoid any lazy loading issues
    for result in results:
        for evidence in result.evidence:
            metadata = evidence.metadata_payload
            if metadata is not None:
                # Always convert to ensure it's a plain dict
                if hasattr(metadata, "model_dump"):
                    evidence.metadata_payload = metadata.model_dump()
                elif hasattr(metadata, "dict"):
                    evidence.metadata_payload = metadata.dict()
                elif not isinstance(metadata, dict):
                    # Try to convert to dict or set to empty
                    try:
                        evidence.metadata_payload = dict(metadata)
                    except (TypeError, ValueError):
                        evidence.metadata_payload = {}

    # Expunge from session to prevent re-loading
    for result in results:
        db.expunge(result)
        for evidence in result.evidence:
            db.expunge(evidence)

    return results


@router.post(
    "/{seeker_identifier}/runs/{run_uuid}/rerun",
    response_model=FactCheckRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerun_fact_check(
    seeker_identifier: int | str,
    run_uuid: UUID,
    request: FactCheckRerunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FactCheckRun:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)
    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_configuration_error_detail(exc),
        ) from exc

    run = (
        db.query(FactCheckRun)
        .filter(
            FactCheckRun.evidence_seeker_id == seeker.id, FactCheckRun.uuid == run_uuid
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Fact-check run not found")

    overrides = request.overrides or {}
    if not overrides and run.config_snapshot:
        overrides = run.config_snapshot.get("overrides") or {}

    new_run = await evidence_seeker_pipeline_manager.create_fact_check_run(
        db=db,
        seeker=seeker,
        statement=run.statement,
        user_id=int(current_user.id),
        overrides=overrides,
    )

    # Schedule the actual execution as a background task
    background_tasks.add_task(
        evidence_seeker_pipeline_manager.execute_fact_check_run,
        run_id=int(new_run.id),
        seeker_id=int(seeker.id),
    )

    return new_run


@router.delete(
    "/{seeker_identifier}/runs/{run_uuid}",
)
def cancel_fact_check_run(
    seeker_identifier: int | str,
    run_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    seeker = get_evidence_seeker_by_identifier(
        seeker_identifier, db, int(current_user.id)
    )
    _ensure_admin(int(current_user.id), seeker, db)

    run = (
        db.query(FactCheckRun)
        .filter(
            FactCheckRun.evidence_seeker_id == seeker.id, FactCheckRun.uuid == run_uuid
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Fact-check run not found")

    if run.status in {FactCheckRunStatus.SUCCEEDED, FactCheckRunStatus.FAILED}:
        return {"detail": "Run already finished"}

    run.status = FactCheckRunStatus.CANCELLED
    run.completed_at = run.completed_at or datetime.utcnow()
    run.error_message = "Run cancelled by user"
    db.commit()

    if run.operation_id:
        progress_tracker.cancel_operation(
            run.operation_id,
            message="Run cancelled by user",
            metadata={"run_uuid": str(run.uuid)},
        )

    return {"detail": "Run cancelled"}
