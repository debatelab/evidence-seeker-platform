from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.auth import fastapi_users
from app.core.database import get_db
from app.core.permissions import (
    get_user_permissions,
    require_evidence_seeker_admin_by_identifier,
    require_platform_admin,
)
from app.models.evidence_seeker import EvidenceSeeker
from app.models.permission import Permission, UserRole
from app.models.user import User
from app.schemas.permission import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    UserPermissions,
)


class UserSearchResult(BaseModel):
    """Schema for user search results without email exposure"""

    id: int
    username: str

    class Config:
        from_attributes = True


class EvidenceSeekerUser(BaseModel):
    """Schema for users with roles on an evidence seeker"""

    id: int
    username: str
    role: UserRole

    class Config:
        from_attributes = True


class RoleAssignmentRequest(BaseModel):
    """Schema for role assignment requests"""

    user_id: int
    role: UserRole


router = APIRouter()


@router.get("/me", response_model=UserPermissions)
async def get_my_permissions(
    current_user: User = Depends(fastapi_users.current_user()),
    db: Session = Depends(get_db),
) -> UserPermissions:
    """
    Get all permissions for the current authenticated user.
    Any authenticated user can view their own permissions.
    """
    try:
        permissions = get_user_permissions(int(current_user.id), db)
        permission_reads = [PermissionRead.model_validate(perm) for perm in permissions]

        return UserPermissions(
            userId=int(current_user.id), permissions=permission_reads
        )
    except Exception as e:
        # Log the error for debugging
        import logging

        logging.error(
            f"Error fetching permissions for user {current_user.id}: {str(e)}"
        )
        # Return empty permissions instead of crashing
        return UserPermissions(userId=int(current_user.id), permissions=[])


@router.post("/", response_model=PermissionRead)
async def create_permission(
    permission: PermissionCreate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> PermissionRead:
    """
    Create a new permission for a user on an evidence seeker.
    Only platform admins can create permissions.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == permission.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if evidence seeker exists
    evidence_seeker = (
        db.query(EvidenceSeeker)
        .filter(EvidenceSeeker.id == permission.evidence_seeker_id)
        .first()
    )
    if not evidence_seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence seeker not found"
        )

    # Check if permission already exists
    existing_permission = (
        db.query(Permission)
        .filter(
            and_(
                Permission.user_id == permission.user_id,
                Permission.evidence_seeker_id == permission.evidence_seeker_id,
            )
        )
        .first()
    )
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already exists for this user and evidence seeker",
        )

    # Create new permission
    db_permission = Permission(
        user_id=permission.user_id,
        evidence_seeker_id=permission.evidence_seeker_id,
        role=UserRole(permission.role.value),
    )
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)

    return PermissionRead.model_validate(db_permission)


@router.get("/{permission_id}", response_model=PermissionRead)
async def get_permission(
    permission_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> PermissionRead:
    """
    Get a specific permission by ID.
    Only platform admins can view permissions.
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    return PermissionRead.model_validate(permission)


@router.put("/{permission_id}", response_model=PermissionRead)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> PermissionRead:
    """
    Update an existing permission.
    Only platform admins can update permissions.
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    # Update fields if provided
    if permission_update.role is not None:
        # SQLAlchemy models declare columns at class level; mypy sees Column[Any].
        # At runtime this is a UserRole enum on instances.
        permission.role = UserRole(permission_update.role.value)  # type: ignore[assignment]

    db.commit()
    db.refresh(permission)

    return PermissionRead.model_validate(permission)


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a permission.
    Only platform admins can delete permissions.
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    db.delete(permission)
    db.commit()

    return {"message": "Permission deleted successfully"}


@router.get("/user/{user_id}", response_model=UserPermissions)
async def get_user_permissions_endpoint(
    user_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> UserPermissions:
    """
    Get all permissions for a specific user.
    Only platform admins can view user permissions.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    permissions = get_user_permissions(user_id, db)
    permission_reads = [PermissionRead.model_validate(perm) for perm in permissions]

    return UserPermissions(userId=user_id, permissions=permission_reads)


@router.get("/", response_model=list[PermissionRead])
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[PermissionRead]:
    """
    List all permissions with pagination.
    Only platform admins can list permissions.
    """
    permissions = db.query(Permission).offset(skip).limit(limit).all()
    return [PermissionRead.model_validate(perm) for perm in permissions]


# Evidence Seeker Permission Management Endpoints


@router.get(
    "/evidence-seeker/{evidence_seeker_identifier}/users",
    response_model=list[EvidenceSeekerUser],
)
async def get_evidence_seeker_users(
    evidence_seeker_identifier: str,
    current_user: User = Depends(require_evidence_seeker_admin_by_identifier()),
    db: Session = Depends(get_db),
) -> list[EvidenceSeekerUser]:
    """
    Get all users with permissions on a specific evidence seeker.
    Only evse_admins of the evidence seeker can view users.
    Returns usernames only (no emails) for GDPR compliance.
    Accepts both UUID and integer ID for backward compatibility.
    """
    # Convert identifier to evidence seeker
    from uuid import UUID

    try:
        # Try as UUID first
        uuid_obj = UUID(evidence_seeker_identifier)
        evidence_seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # Try as integer ID
        try:
            evidence_seeker_id = int(evidence_seeker_identifier)
            evidence_seeker = (
                db.query(EvidenceSeeker)
                .filter(EvidenceSeeker.id == evidence_seeker_id)
                .first()
            )
        except (ValueError, TypeError):
            evidence_seeker = None

    if not evidence_seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence seeker not found"
        )

    # Get all permissions for this evidence seeker
    permissions = (
        db.query(Permission)
        .filter(Permission.evidence_seeker_id == int(evidence_seeker.id))
        .all()
    )

    # Build response with user details (usernames only)
    result = []
    for perm in permissions:
        user = db.query(User).filter(User.id == perm.user_id).first()
        if user:
            result.append(
                EvidenceSeekerUser(
                    id=int(user.id),
                    username=cast(str, user.username),
                    role=cast(UserRole, perm.role),
                )
            )

    return result


@router.post("/evidence-seeker/{evidence_seeker_identifier}/assign")
async def assign_evidence_seeker_role(
    evidence_seeker_identifier: str,
    request: RoleAssignmentRequest,
    current_user: User = Depends(require_evidence_seeker_admin_by_identifier()),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Assign a role to a user for a specific evidence seeker.
    Only evse_admins of the evidence seeker can assign roles.
    Accepts both UUID and integer ID for backward compatibility.
    """
    # Convert identifier to evidence seeker
    from uuid import UUID

    try:
        # Try as UUID first
        uuid_obj = UUID(evidence_seeker_identifier)
        evidence_seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # Try as integer ID
        try:
            evidence_seeker_id = int(evidence_seeker_identifier)
            evidence_seeker = (
                db.query(EvidenceSeeker)
                .filter(EvidenceSeeker.id == evidence_seeker_id)
                .first()
            )
        except (ValueError, TypeError):
            evidence_seeker = None

    if not evidence_seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence seeker not found"
        )

    # Verify target user exists
    target_user = db.query(User).filter(User.id == request.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found"
        )

    # Check if permission already exists
    existing_permission = (
        db.query(Permission)
        .filter(
            and_(
                Permission.user_id == request.user_id,
                Permission.evidence_seeker_id == int(evidence_seeker.id),
            )
        )
        .first()
    )

    if existing_permission:
        # Update existing permission
        # Mypy considers the attribute type Column[Any] due to SQLAlchemy; safe at runtime.
        existing_permission.role = request.role  # type: ignore[assignment]
        db.commit()
        return {"message": "Role updated successfully"}
    else:
        # Create new permission
        new_permission = Permission(
            user_id=request.user_id,
            evidence_seeker_id=int(evidence_seeker.id),
            role=request.role,
        )
        db.add(new_permission)
        db.commit()
        return {"message": "Role assigned successfully"}


@router.delete("/evidence-seeker/{evidence_seeker_identifier}/users/{user_id}")
async def remove_evidence_seeker_user(
    evidence_seeker_identifier: str,
    user_id: int,
    current_user: User = Depends(require_evidence_seeker_admin_by_identifier()),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Remove a user's access to a specific evidence seeker.
    Only evse_admins of the evidence seeker can remove users.
    Accepts both UUID and integer ID for backward compatibility.
    """
    # Convert identifier to evidence seeker
    from uuid import UUID

    try:
        # Try as UUID first
        uuid_obj = UUID(evidence_seeker_identifier)
        evidence_seeker = (
            db.query(EvidenceSeeker).filter(EvidenceSeeker.uuid == uuid_obj).first()
        )
    except (ValueError, TypeError):
        # Try as integer ID
        try:
            evidence_seeker_id = int(evidence_seeker_identifier)
            evidence_seeker = (
                db.query(EvidenceSeeker)
                .filter(EvidenceSeeker.id == evidence_seeker_id)
                .first()
            )
        except (ValueError, TypeError):
            evidence_seeker = None

    if not evidence_seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence seeker not found"
        )

    # Find and delete the permission
    permission = (
        db.query(Permission)
        .filter(
            and_(
                Permission.user_id == user_id,
                Permission.evidence_seeker_id == evidence_seeker.id,
            )
        )
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have access to this evidence seeker",
        )

    db.delete(permission)
    db.commit()

    return {"message": "User access removed successfully"}


# Platform Admin Permission Management Endpoints


@router.post("/platform-admin/{user_id}")
async def grant_platform_admin(
    user_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Grant PLATFORM_ADMIN role to a user.
    Only platform admins can grant platform admin access.
    """
    # Check if target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if permission already exists
    existing_permission = (
        db.query(Permission)
        .filter(
            and_(
                Permission.user_id == user_id,
                Permission.role == UserRole.PLATFORM_ADMIN,
            )
        )
        .first()
    )

    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has platform admin access",
        )

    # Create new platform admin permission
    new_permission = Permission(
        user_id=user_id,
        evidence_seeker_id=None,  # Platform admin has no specific evidence seeker
        role=UserRole.PLATFORM_ADMIN,
    )
    db.add(new_permission)
    db.commit()

    return {"message": "Platform admin access granted successfully"}


@router.delete("/platform-admin/{user_id}")
async def revoke_platform_admin(
    user_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Revoke PLATFORM_ADMIN role from a user.
    Only platform admins can revoke platform admin access.
    """
    # Prevent revoking own platform admin access
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke your own platform admin access",
        )

    # Check if target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Find and delete the platform admin permission
    permission = (
        db.query(Permission)
        .filter(
            and_(
                Permission.user_id == user_id,
                Permission.role == UserRole.PLATFORM_ADMIN,
            )
        )
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have platform admin access",
        )

    db.delete(permission)
    db.commit()

    return {"message": "Platform admin access revoked successfully"}
