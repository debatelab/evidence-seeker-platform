import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import get_current_user
from ..core.config import settings
from ..core.database import get_db
from ..core.file_utils import delete_file
from ..core.permissions import (
    check_evidence_seeker_permission,
    get_user_permissions,
)
from ..models.evidence_seeker import EvidenceSeeker
from ..models.permission import UserRole
from ..models.user import User
from ..schemas.evidence_seeker import (
    EvidenceSeekerCreate,
    EvidenceSeekerRead,
    EvidenceSeekerUpdate,
)

router = APIRouter()


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
            select(EvidenceSeeker).where(EvidenceSeeker.uuid == uuid_obj)
        )
        seeker = result.scalar_one_or_none()
    except (ValueError, TypeError):
        # If not UUID, treat as integer ID
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.id == int(identifier))
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
    # Get user's permissions
    permissions = get_user_permissions(user_id, db)

    # Collect evidence seeker IDs the user has access to
    accessible_ids = set()
    for permission in permissions:
        accessible_ids.add(permission.evidence_seeker_id)

    # Also include evidence seekers created by the user or public ones
    result = db.execute(
        select(EvidenceSeeker).where(
            (EvidenceSeeker.created_by == user_id) | EvidenceSeeker.is_public
        )
    )
    created_or_public = result.scalars().all()

    for seeker in created_or_public:
        accessible_ids.add(seeker.id)

    if accessible_ids:
        result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.id.in_(list(accessible_ids)))
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
    db_seeker = EvidenceSeeker(**seeker.dict(), created_by=current_user.id)
    db.add(db_seeker)
    db.commit()
    db.refresh(db_seeker)
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

    for field, value in seeker_update.dict(exclude_unset=True).items():
        setattr(seeker, field, value)
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
    from ..models.document import Document

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
