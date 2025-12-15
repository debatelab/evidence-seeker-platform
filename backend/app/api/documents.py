import asyncio
import logging
import os
from collections.abc import Coroutine, Sequence
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import AnyHttpUrl, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from ..core.auth import User, get_current_user
from ..core.config import settings
from ..core.database import get_db
from ..core.evidence_seeker_config_service import (
    ConfigurationNotReadyError,
    evidence_seeker_config_service,
)
from ..core.evidence_seeker_index_service import evidence_seeker_index_service
from ..core.file_utils import delete_file, save_upload_file, validate_file
from ..core.onboarding_tokens import onboarding_token_service
from ..core.permissions import check_evidence_seeker_permission
from ..core.progress_tracker import progress_tracker
from ..models.document import Document
from ..models.evidence_seeker import EvidenceSeeker
from ..models.index_job import IndexJob, IndexJobStatus
from ..models.permission import UserRole
from ..models.user import ensure_user_id
from ..schemas.document import DocumentIngestionResponse, DocumentRead, DocumentUpdate

router = APIRouter()

logger = logging.getLogger(__name__)


def _config_guard_detail(exc: ConfigurationNotReadyError) -> dict[str, object]:
    payload = evidence_seeker_config_service.serialise_status(exc.status)
    payload.setdefault("message", "Evidence Seeker configuration incomplete")
    return payload


def _run_async_task(coro: Coroutine[Any, Any, None]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


def _process_index_update(job_id: int, document_ids: list[int]) -> None:
    from ..core.database import SessionLocal

    async def _run() -> None:
        db = SessionLocal()
        try:
            job = db.get(IndexJob, job_id)
            if job is None:
                return
            seeker = db.get(EvidenceSeeker, job.evidence_seeker_id)
            if seeker is None:
                return
            documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
            if not documents:
                return

            await evidence_seeker_index_service.run_update(db, job, seeker, documents)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Index update job %s failed", job_id)
            try:
                db.rollback()
            except Exception:  # pragma: no cover
                logger.exception("Rollback failed after job %s error", job_id)
            job = db.get(IndexJob, job_id)
            seeker = None
            if job is not None:
                seeker = db.get(EvidenceSeeker, job.evidence_seeker_id)
            if job is not None and seeker is not None:
                try:
                    evidence_seeker_index_service._update_job_status(
                        db,
                        job,
                        IndexJobStatus.FAILED,
                        message="Index update failed",
                        error=str(exc),
                    )
                except Exception:  # pragma: no cover - best-effort failure reporting
                    logger.exception(
                        "Failed to record failure for index update job %s", job_id
                    )
        finally:
            db.close()

    _run_async_task(_run())


def _process_index_delete(job_id: int, document_ids: list[int]) -> None:
    from ..core.database import SessionLocal

    async def _run() -> None:
        db = SessionLocal()
        try:
            job = db.get(IndexJob, job_id)
            if job is None:
                return
            seeker = db.get(EvidenceSeeker, job.evidence_seeker_id)
            if seeker is None:
                return
            documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
            if not documents:
                return

            await evidence_seeker_index_service.run_delete(db, job, seeker, documents)
            for document in documents:
                delete_file(document.file_path)
                db.delete(document)
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Index delete job %s failed", job_id)
            try:
                db.rollback()
            except Exception:  # pragma: no cover
                logger.exception("Rollback failed after job %s delete error", job_id)
            job = db.get(IndexJob, job_id)
            seeker = None
            if job is not None:
                seeker = db.get(EvidenceSeeker, job.evidence_seeker_id)
            if job is not None and seeker is not None:
                try:
                    evidence_seeker_index_service._update_job_status(
                        db,
                        job,
                        IndexJobStatus.FAILED,
                        message="Index delete failed",
                        error=str(exc),
                    )
                except Exception:  # pragma: no cover - best-effort failure reporting
                    logger.exception(
                        "Failed to record failure for index delete job %s", job_id
                    )
        finally:
            db.close()

    _run_async_task(_run())


def _validate_source_url(raw_url: Any | None) -> str | None:
    """Normalize and validate an optional source URL."""
    if raw_url is None:
        return None
    # Accept AnyHttpUrl instances or raw strings
    value = str(raw_url).strip()
    if value == "":
        return None
    try:
        validated = TypeAdapter(AnyHttpUrl).validate_python(value)
        return str(validated)
    except ValidationError as exc:  # pragma: no cover - validation path
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid source_url; must be a valid http(s) URL.",
        ) from exc


@router.post("/upload", response_model=DocumentIngestionResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    source_url: str | None = Form(None, alias="sourceUrl"),
    evidence_seeker_uuid: str = Form(...),  # Use UUID for external API
    onboarding_token: str | None = Header(default=None, alias="X-Onboarding-Token"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentIngestionResponse:
    """Upload a new document - requires admin permissions for the evidence seeker"""
    # Validate file
    if not validate_file(file):
        raise HTTPException(status_code=400, detail="Invalid file type or size")

    # Get the evidence seeker (permission check already done in dependency)
    try:
        uuid_obj = UUID(evidence_seeker_uuid)
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=404, detail="Invalid evidence seeker UUID"
        ) from None

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check admin permissions for the evidence seeker
    # Extract scalar seeker_id value
    seeker_id = int(seeker.id)
    current_user_id = ensure_user_id(current_user)
    if not check_evidence_seeker_permission(
        current_user_id, seeker_id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )
    allow_onboarding_upload = False
    if onboarding_token:
        allow_onboarding_upload = onboarding_token_service.verify_token(
            onboarding_token,
            seeker,
            current_user_id,
        )

    try:
        evidence_seeker_config_service.require_ready(db, seeker)
    except ConfigurationNotReadyError as exc:
        missing_requirements = set(exc.status.missing_requirements)
        # Allow first-time uploads even when the seeker is missing documents,
        # but still block when credentials or other requirements are missing.
        documents_only_missing = missing_requirements == {"DOCUMENTS"}
        if onboarding_token and not allow_onboarding_upload:
            detail = _config_guard_detail(exc)
            detail["message"] = "Invalid onboarding token"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc
        if not documents_only_missing and not allow_onboarding_upload:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_config_guard_detail(exc),
            ) from exc

    # Save file and get file info
    file_path = save_upload_file(file, seeker_id)

    # Get file size after saving (or read file content)
    file_size = 0
    try:
        # Read the file to get its size
        with open(file_path, "rb") as f:
            content = f.read()
            file_size = len(content)
    except Exception as e:
        print(f"Warning: Could not read file size from {file_path}: {e}")
        # Fallback: try to get size from upload file if available
        file_size = getattr(file, "size", 0)

    # Ensure we have a valid file size
    if file_size == 0 and hasattr(file, "size") and file.size:
        file_size = file.size

    # Determine mime type more reliably
    mime_type = file.content_type
    if not mime_type or mime_type == "application/octet-stream":
        # Try to determine from file extension
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        elif filename.lower().endswith(".txt"):
            mime_type = "text/plain"
        else:
            mime_type = "application/octet-stream"

    # Get original filename from upload
    original_filename = file.filename or "unnamed_file"

    # Create document with all required fields
    db_document = Document()
    db_document.title = title
    db_document.description = description
    db_document.file_path = file_path
    db_document.original_filename = original_filename
    db_document.file_size = max(file_size, 0)
    db_document.mime_type = mime_type
    db_document.evidence_seeker_id = seeker_id
    db_document.evidence_seeker_uuid = uuid_obj
    db_document.source_url = _validate_source_url(source_url)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    job = evidence_seeker_index_service.queue_update(
        db=db,
        seeker=seeker,
        user_id=int(current_user.id),
        documents=[db_document],
    )

    background_tasks.add_task(
        _process_index_update,
        job.id,
        [int(db_document.id)],
    )

    response_payload = DocumentIngestionResponse.model_validate(
        {
            "document": db_document,
            "job_uuid": job.uuid,
            "operation_id": job.operation_id,
        }
    )
    if allow_onboarding_upload:
        progress_tracker.record_event(
            "evse_onboarding_document_uploaded",
            user_id=current_user_id,
            evidence_seeker_id=seeker_id,
            metadata={"document_uuid": str(db_document.uuid)},
        )
    return response_payload


@router.get("/", response_model=list[DocumentRead])
def get_documents(
    evidence_seeker_uuid: str,  # Use UUID for external API
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[Document]:
    """Get all documents for an Evidence Seeker - requires reader permissions"""
    # Get the evidence seeker
    try:
        uuid_obj = UUID(evidence_seeker_uuid)
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=404, detail="Invalid evidence seeker UUID"
        ) from None

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Extract scalar seeker_id value
    seeker_id = int(seeker.id)
    user_id = ensure_user_id(current_user)

    # Check reader permissions
    if not check_evidence_seeker_permission(
        user_id, seeker_id, UserRole.EVSE_READER, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: read access required",
        )

    documents = (
        db.query(Document)
        .filter(Document.evidence_seeker_id == seeker_id)  # Use internal integer ID
        .all()
    )
    return documents


def require_document_reader(
    document_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to check if user can read a document"""
    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Extract scalar evidence_seeker_id value
    evidence_seeker_id = int(document.evidence_seeker_id)

    # Check if user has read access to the evidence seeker
    if not check_evidence_seeker_permission(
        ensure_user_id(current_user), evidence_seeker_id, UserRole.EVSE_READER, db
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        )

    return current_user


@router.get("/{document_uuid}/download")
def download_document(
    document_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_reader),
) -> FileResponse:
    """Download a document by UUID - requires reader permissions"""
    from uuid import UUID

    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Extract scalar values for FileResponse
    file_path = document.file_path
    media_type = document.mime_type
    original_filename = document.original_filename

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file with original filename
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=original_filename,
    )


def require_document_admin(
    document_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to check if user can administer a document"""
    from uuid import UUID

    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user has admin access to the evidence seeker
    # Extract scalar evidence_seeker_id value
    evidence_seeker_id = int(document.evidence_seeker_id)
    if not check_evidence_seeker_permission(
        ensure_user_id(current_user), evidence_seeker_id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this document"
        )

    return current_user


@router.patch("/{document_uuid}", response_model=DocumentRead)
def update_document(
    document_uuid: str,
    payload: DocumentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_admin),
) -> Document:
    """Update document metadata; URL-only updates do not trigger reindex."""
    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    seeker = db.get(EvidenceSeeker, document.evidence_seeker_id)
    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    updated = False
    reindex_required = False

    fields_set = payload.model_fields_set

    if "title" in fields_set and payload.title is not None:
        if payload.title != document.title:
            document.title = payload.title
            updated = True
            reindex_required = True

    if "description" in fields_set:
        if payload.description != document.description:
            document.description = payload.description
            updated = True
            reindex_required = True

    if "source_url" in fields_set:
        new_url = _validate_source_url(payload.source_url)
        if new_url != document.source_url:
            document.source_url = new_url
            updated = True

    if not updated:
        return document

    db.add(document)
    db.commit()
    db.refresh(document)

    if reindex_required:
        job = evidence_seeker_index_service.queue_update(
            db=db,
            seeker=seeker,
            user_id=ensure_user_id(current_user),
            documents=[document],
        )
        background_tasks.add_task(_process_index_update, job.id, [int(document.id)])

    return document


@router.delete("/{document_uuid}")
def delete_document(
    document_uuid: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_admin),
) -> dict[str, str]:
    """Delete a document by UUID - requires admin permissions"""
    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    seeker = db.get(EvidenceSeeker, document.evidence_seeker_id)
    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    if settings.disable_embeddings:
        # When embeddings are disabled (tests/CI), skip async index cleanup and
        # delete the record synchronously to avoid requiring HF keys or loops.
        delete_file(document.file_path)
        db.delete(document)
        db.commit()
        return {
            "detail": "Document deletion scheduled",
            "jobUuid": "",
            "operationId": "",
        }

    user_id = ensure_user_id(current_user)
    job = evidence_seeker_index_service.queue_delete(
        db=db,
        seeker=seeker,
        user_id=user_id,
        documents=[document],
    )

    # Run the delete job synchronously so the document is removed before the
    # response returns. This keeps behaviour deterministic in tests and avoids
    # dangling rows when background tasks are not awaited.
    _process_index_delete(
        job.id,
        [int(document.id)],
    )

    return {
        "detail": "Document deletion scheduled",
        "jobUuid": str(job.uuid),
        "operationId": job.operation_id or "",
    }
