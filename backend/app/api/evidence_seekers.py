from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Union
from uuid import UUID
import shutil
import os
from pathlib import Path
from ..core.database import get_db
from ..schemas.evidence_seeker import (
    EvidenceSeekerCreate,
    EvidenceSeekerRead,
    EvidenceSeekerUpdate,
)
from ..models.evidence_seeker import EvidenceSeeker
from ..core.auth import get_current_user
from ..core.permissions import (
    require_evidence_seeker_admin,
    require_evidence_seeker_reader,
    check_evidence_seeker_permission,
    get_user_permissions,
)
from ..models.permission import UserRole
from ..core.file_utils import delete_file
from ..core.config import settings


router = APIRouter()


def get_evidence_seeker_by_identifier(
    identifier: Union[int, str],
    db: Session,
    current_user_id: int,
) -> EvidenceSeeker:
    """Helper function to get Evidence Seeker by ID or UUID with permission check"""
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(identifier))
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        seeker = (
            db.query(EvidenceSeeker)
            .filter(EvidenceSeeker.id == int(identifier))
            .first()
        )

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check if user has read access to this evidence seeker
    if not check_evidence_seeker_permission(
        current_user_id, seeker.id, UserRole.EVSE_READER, db
    ):
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    return seeker


def get_accessible_evidence_seekers(user_id: int, db: Session) -> List[EvidenceSeeker]:
    """Get all evidence seekers accessible to a user based on permissions"""
    # Get user's permissions
    permissions = get_user_permissions(user_id, db)

    # Collect evidence seeker IDs the user has access to
    accessible_ids = set()
    for permission in permissions:
        accessible_ids.add(permission.evidence_seeker_id)

    # Also include evidence seekers created by the user or public ones
    created_or_public = (
        db.query(EvidenceSeeker)
        .filter(
            (EvidenceSeeker.created_by == user_id) | (EvidenceSeeker.is_public == True)
        )
        .all()
    )

    for seeker in created_or_public:
        accessible_ids.add(seeker.id)

    if accessible_ids:
        return (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.id.in_(accessible_ids)).all()
        )
    return []


@router.post("/", response_model=EvidenceSeekerRead)
def create_evidence_seeker(
    seeker: EvidenceSeekerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new Evidence Seeker"""
    db_seeker = EvidenceSeeker(**seeker.dict(), created_by=current_user.id)
    db.add(db_seeker)
    db.commit()
    db.refresh(db_seeker)
    return db_seeker


@router.get("/", response_model=List[EvidenceSeekerRead])
def get_evidence_seekers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all Evidence Seekers accessible to the current user"""
    seekers = get_accessible_evidence_seekers(current_user.id, db)
    return seekers[skip : skip + limit]


@router.get("/{seeker_id}", response_model=EvidenceSeekerRead)
def get_evidence_seeker(
    seeker_id: Union[int, str],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific Evidence Seeker by ID or UUID"""
    return get_evidence_seeker_by_identifier(seeker_id, db, current_user.id)


@router.put("/{seeker_id}", response_model=EvidenceSeekerRead)
def update_evidence_seeker(
    seeker_id: Union[int, str],
    seeker_update: EvidenceSeekerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an Evidence Seeker - requires admin permissions"""
    # Get the seeker first to check permissions
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(seeker_id))
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.id == int(seeker_id)).first()
        )

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check admin permissions
    if not check_evidence_seeker_permission(
        current_user.id, seeker.id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )

    for field, value in seeker_update.dict(exclude_unset=True).items():
        setattr(seeker, field, value)
    db.commit()
    db.refresh(seeker)
    return seeker


@router.delete("/{seeker_id}")
def delete_evidence_seeker(
    seeker_id: Union[int, str],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete an Evidence Seeker - requires admin permissions"""
    # Get the seeker first to check permissions
    try:
        # Try to parse as UUID first
        uuid_obj = UUID(str(seeker_id))
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.id == int(seeker_id)).first()
        )

    if seeker is None:
        raise HTTPException(status_code=404, detail="Evidence Seeker not found")

    # Check admin permissions
    if not check_evidence_seeker_permission(
        current_user.id, seeker.id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )

    # Delete all associated documents and their files
    from ..models.document import Document

    documents = (
        db.query(Document).filter(Document.evidence_seeker_id == seeker.id).all()
    )

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
