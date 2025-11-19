from typing import overload

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.evidence_seeker import EvidenceSeeker
from app.models.permission import Permission, UserRole
from app.models.user import User, ensure_user_id


def _require_user_id(user: User) -> int:
    """Extract a concrete user ID, raising if the ORM object is incomplete."""
    try:
        return ensure_user_id(user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user has no ID",
        ) from exc


def check_evidence_seeker_permission(
    user_id: int, evidence_seeker_id: int, required_role: UserRole, db: Session
) -> bool:
    """
    Check if user has required role for evidence seeker.

    Args:
        user_id: The user ID to check permissions for
        evidence_seeker_id: The evidence seeker ID to check access for
        required_role: The minimum role required (EVSE_READER, EVSE_ADMIN, or PLATFORM_ADMIN)
        db: Database session

    Returns:
        bool: True if user has permission, False otherwise
    """
    # If PLATFORM_ADMIN is required, only a platform admin role satisfies it
    if required_role == UserRole.PLATFORM_ADMIN:
        result = db.execute(
            select(Permission).where(
                and_(
                    Permission.user_id == user_id,
                    Permission.role == UserRole.PLATFORM_ADMIN,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    # First check if user is a platform admin - they have global access to everything
    result = db.execute(
        select(Permission).where(
            and_(
                Permission.user_id == user_id,
                Permission.role == UserRole.PLATFORM_ADMIN,
            )
        )
    )
    platform_admin_permission = result.scalar_one_or_none()
    if platform_admin_permission:
        return True

    # Treat the creator/owner of the evidence seeker as having EVSE_ADMIN access
    # Only applicable when a concrete evidence_seeker_id is provided (> 0)
    if evidence_seeker_id and evidence_seeker_id > 0:
        es_result = db.execute(
            select(EvidenceSeeker).where(EvidenceSeeker.id == evidence_seeker_id)
        )
        seeker = es_result.scalar_one_or_none()
        if seeker and int(seeker.created_by) == int(user_id):
            # Owner can perform admin or reader actions on their seeker
            return required_role in (UserRole.EVSE_ADMIN, UserRole.EVSE_READER)

    # Check specific evidence seeker permissions
    result = db.execute(
        select(Permission).where(
            and_(
                Permission.user_id == user_id,
                Permission.evidence_seeker_id == evidence_seeker_id,
            )
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        return False

    # Check role hierarchy: PLATFORM_ADMIN > EVSE_ADMIN > EVSE_READER
    role_hierarchy = {
        UserRole.PLATFORM_ADMIN: 3,
        UserRole.EVSE_ADMIN: 2,
        UserRole.EVSE_READER: 1,
    }

    permission_role: UserRole = UserRole(permission.role.value)
    user_level: int = role_hierarchy.get(permission_role, 0)
    required_level: int = role_hierarchy.get(required_role, 0)

    return user_level >= required_level


def get_user_permissions(user_id: int, db: Session) -> list[Permission]:
    """
    Retrieve all permissions for a user.

    Args:
        user_id: The user ID to get permissions for
        db: Database session

    Returns:
        List[Permission]: List of user's permissions
    """
    result = db.execute(select(Permission).where(Permission.user_id == user_id))
    permissions = list(result.scalars().all())
    return permissions


class RequireEvidenceSeekerAdmin:
    """Dependency class for admin-only operations on evidence seekers."""

    def __init__(self, evidence_seeker_id: int):
        self.evidence_seeker_id = evidence_seeker_id

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        """
        Check if user has admin access to the evidence seeker.

        Args:
            current_user: The authenticated user
            db: Database session

        Returns:
            User: The authenticated user if they have admin access

        Raises:
            HTTPException: If user doesn't have admin access
        """
        if not check_evidence_seeker_permission(
            _require_user_id(current_user),
            self.evidence_seeker_id,
            UserRole.EVSE_ADMIN,
            db,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions: admin access required",
            )
        return current_user


@overload
def require_evidence_seeker_admin(
    evidence_seeker_id: int,
) -> RequireEvidenceSeekerAdmin: ...


@overload
def require_evidence_seeker_admin(
    evidence_seeker_id: int, current_user: User, db: Session
) -> User: ...


def require_evidence_seeker_admin(
    evidence_seeker_id: int, current_user: User | None = None, db: Session | None = None
) -> RequireEvidenceSeekerAdmin | User:
    """
    Evidence seeker admin dependency.

    - When called with only evidence_seeker_id, returns a FastAPI dependency object.
    - When called with (evidence_seeker_id, current_user, db), performs the check and returns the user.
    """
    if current_user is None or db is None:
        return RequireEvidenceSeekerAdmin(evidence_seeker_id)

    if not check_evidence_seeker_permission(
        _require_user_id(current_user), evidence_seeker_id, UserRole.EVSE_ADMIN, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
        )
    return current_user


def require_evidence_seeker_reader(
    evidence_seeker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for read operations on evidence seekers.

    Args:
        evidence_seeker_id: The evidence seeker ID to check access for
        current_user: The authenticated user
        db: Database session

    Returns:
        User: The authenticated user if they have read access

    Raises:
        HTTPException: If user doesn't have read access
    """
    if not check_evidence_seeker_permission(
        _require_user_id(current_user), evidence_seeker_id, UserRole.EVSE_READER, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: read access required",
        )
    return current_user


def require_platform_admin(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """
    Dependency for platform admin operations.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        User: The authenticated user if they are a platform admin

    Raises:
        HTTPException: If user is not a platform admin
    """
    if not check_evidence_seeker_permission(
        _require_user_id(current_user),
        0,
        UserRole.PLATFORM_ADMIN,
        db,  # evidence_seeker_id not needed for platform admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: platform admin access required",
        )
    return current_user


class RequireEvidenceSeekerAdminByIdentifier:
    """Dependency class for admin-only operations on evidence seekers by identifier (UUID or int)."""

    def __init__(self, identifier_param: str = "evidence_seeker_identifier"):
        self.identifier_param = identifier_param

    def __call__(
        self,
        evidence_seeker_identifier: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        """
        Check if user has admin access to the evidence seeker identified by UUID or int.

        Args:
            evidence_seeker_identifier: The evidence seeker identifier (UUID string or int)
            current_user: The authenticated user
            db: Database session

        Returns:
            User: The authenticated user if they have admin access

        Raises:
            HTTPException: If user doesn't have admin access or evidence seeker not found
        """
        from uuid import UUID

        from app.models.evidence_seeker import EvidenceSeeker

        # Convert identifier to evidence seeker
        try:
            # Try as UUID first
            uuid_obj = UUID(evidence_seeker_identifier)
            result = db.execute(
                select(EvidenceSeeker).where(EvidenceSeeker.uuid == uuid_obj)
            )
            evidence_seeker = result.scalar_one_or_none()
        except (ValueError, TypeError):
            # Try as integer ID
            try:
                evidence_seeker_id = int(evidence_seeker_identifier)
                result = db.execute(
                    select(EvidenceSeeker).where(
                        EvidenceSeeker.id == evidence_seeker_id
                    )
                )
                evidence_seeker = result.scalar_one_or_none()
            except (ValueError, TypeError):
                evidence_seeker = None

        if not evidence_seeker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence seeker not found",
            )

        # Check if user is a platform admin (has global access)
        platform_admin_check = check_evidence_seeker_permission(
            _require_user_id(current_user), 0, UserRole.PLATFORM_ADMIN, db
        )
        if not platform_admin_check:
            # If not a platform admin, check for evidence seeker specific admin access
            if not check_evidence_seeker_permission(
                _require_user_id(current_user),
                int(evidence_seeker.id),
                UserRole.EVSE_ADMIN,
                db,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions: admin access required",
                )
        return current_user


def require_evidence_seeker_admin_by_identifier(
    identifier_param: str = "evidence_seeker_identifier",
) -> RequireEvidenceSeekerAdminByIdentifier:
    """
    Factory function for evidence seeker admin dependency by identifier.

    Args:
        identifier_param: The parameter name containing the identifier

    Returns:
        RequireEvidenceSeekerAdminByIdentifier: Dependency instance
    """
    return RequireEvidenceSeekerAdminByIdentifier(identifier_param)
