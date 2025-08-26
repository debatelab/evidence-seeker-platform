from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from ..models.document import Document
from ..models.evidence_seeker import EvidenceSeeker
from ..core.auth import get_current_user
from ..core.file_utils import validate_file, save_upload_file, delete_file


router = APIRouter()


@router.post("/upload", response_model=DocumentRead)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    evidence_seeker_uuid: str = Form(...),  # Use UUID for external API
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a new document"""
    # Validate file
    if not validate_file(file):
        raise HTTPException(status_code=400, detail="Invalid file type or size")

    # Check if evidence_seeker exists and user has access
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=404, detail="Evidence Seeker not found or no access"
        )

    # Save file and get file info
    file_path = save_upload_file(file, seeker.id)

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

    # Create document with all required fields
    db_document = Document(
        title=title,
        description=description,
        file_path=file_path,
        file_size=max(file_size, 0),  # Ensure non-negative
        mime_type=mime_type,
        evidence_seeker_id=seeker.id,  # Use internal integer ID
        evidence_seeker_uuid=evidence_seeker_uuid,  # Use provided UUID
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


@router.get("/", response_model=List[DocumentRead])
def get_documents(
    evidence_seeker_uuid: str,  # Use UUID for external API
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all documents for an Evidence Seeker"""
    # Check access
    from .evidence_seekers import get_evidence_seeker_by_identifier

    try:
        seeker = get_evidence_seeker_by_identifier(
            evidence_seeker_uuid, db, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=404, detail="Evidence Seeker not found or no access"
        )

    documents = (
        db.query(Document)
        .filter(Document.evidence_seeker_id == seeker.id)  # Use internal integer ID
        .all()
    )
    return documents


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user has access to the evidence_seeker
    seeker = (
        db.query(EvidenceSeeker)
        .filter(
            EvidenceSeeker.id == document.evidence_seeker_id,
            EvidenceSeeker.created_by == current_user.id,
        )
        .first()
    )
    if seeker is None:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this document"
        )

    # Delete file
    delete_file(document.file_path)

    # Delete from db
    db.delete(document)
    db.commit()
    return {"detail": "Document deleted"}
