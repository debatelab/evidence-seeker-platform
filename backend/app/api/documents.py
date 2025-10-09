import os
from collections.abc import Sequence
from typing import cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.auth import User, get_current_user
from ..core.database import get_db
from ..core.embedding_service import embedding_service
from ..core.file_utils import delete_file, save_upload_file, validate_file
from ..core.permissions import check_evidence_seeker_permission
from ..models.document import Document
from ..models.evidence_seeker import EvidenceSeeker
from ..models.permission import UserRole
from ..schemas.document import DocumentRead

router = APIRouter()


async def generate_document_embeddings(document_id: int) -> None:
    """Background task to generate embeddings for a document"""
    # Create a new database session for the background task
    from ..core.database import SessionLocal

    db = SessionLocal()
    try:
        # Generate embeddings using the embedding service
        success = await embedding_service.generate_embeddings_for_document(
            document_id, db
        )
        if success:
            print(f"Successfully generated embeddings for document {document_id}")
        else:
            print(f"Failed to generate embeddings for document {document_id}")
    except Exception as e:
        print(f"Error generating embeddings for document {document_id}: {str(e)}")
    finally:
        db.close()


@router.post("/upload", response_model=DocumentRead)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    evidence_seeker_uuid: str = Form(...),  # Use UUID for external API
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Upload a new document - requires admin permissions for the evidence seeker"""
    # Validate file
    if not validate_file(file):
        raise HTTPException(status_code=400, detail="Invalid file type or size")

    # Get the evidence seeker (permission check already done in dependency)
    from uuid import UUID

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
    seeker_id = cast(int, seeker.id)
    if not check_evidence_seeker_permission(
        int(current_user.id), seeker_id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )

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
    db_document = Document(
        title=title,
        description=description,
        file_path=file_path,
        original_filename=original_filename,
        file_size=max(file_size, 0),  # Ensure non-negative
        mime_type=mime_type,
        evidence_seeker_id=seeker_id,  # Use internal integer ID
        evidence_seeker_uuid=evidence_seeker_uuid,  # Use provided UUID
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger embedding generation in the background
    # Extract scalar document_id value
    document_id = cast(int, db_document.id)
    background_tasks.add_task(generate_document_embeddings, document_id)

    return db_document


@router.get("/", response_model=list[DocumentRead])
def get_documents(
    evidence_seeker_uuid: str,  # Use UUID for external API
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[Document]:
    """Get all documents for an Evidence Seeker - requires reader permissions"""
    # Get the evidence seeker
    from uuid import UUID

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
    seeker_id = cast(int, seeker.id)

    # Check reader permissions
    if not check_evidence_seeker_permission(
        int(current_user.id), seeker_id, UserRole.EVSE_READER, db
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
    from uuid import UUID

    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Extract scalar evidence_seeker_id value
    evidence_seeker_id = cast(int, document.evidence_seeker_id)

    # Check if user has read access to the evidence seeker
    if not check_evidence_seeker_permission(
        int(current_user.id), evidence_seeker_id, UserRole.EVSE_READER, db
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
    file_path = cast(str, document.file_path)
    media_type = cast(str, document.mime_type)
    original_filename = cast(str, document.original_filename)

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
    evidence_seeker_id = cast(int, document.evidence_seeker_id)
    if not check_evidence_seeker_permission(
        int(current_user.id), evidence_seeker_id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this document"
        )

    return current_user


@router.delete("/{document_uuid}")
def delete_document(
    document_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_admin),
) -> dict[str, str]:
    """Delete a document by UUID - requires admin permissions"""
    from uuid import UUID

    try:
        uuid_obj = UUID(document_uuid)
        document = db.query(Document).filter(Document.uuid == uuid_obj).first()
    except (ValueError, TypeError):
        document = None

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Extract scalar file_path value
    file_path = cast(str, document.file_path)

    # Delete file
    delete_file(file_path)

    # Delete from db
    db.delete(document)
    db.commit()
    return {"detail": "Document deleted"}
