import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import (
    check_evidence_seeker_permission,
    get_user_permissions,
    require_evidence_seeker_admin,
    require_evidence_seeker_reader,
    require_platform_admin,
)
from app.models.evidence_seeker import EvidenceSeeker
from app.models.permission import Permission, UserRole
from app.models.user import User


def test_check_evidence_seeker_permission_platform_admin(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test platform admin has access to all evidence seekers"""
    # Create platform admin permission
    platform_admin_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,  # associate with an existing seeker to satisfy FK
        role=UserRole.PLATFORM_ADMIN,
    )
    db.add(platform_admin_perm)
    db.commit()

    # Platform admin should have access to any evidence seeker
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_READER, db
    )
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_ADMIN, db
    )
    assert check_evidence_seeker_permission(
        int(test_user.id), 999, UserRole.EVSE_ADMIN, db
    )


def test_check_evidence_seeker_permission_evse_admin(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test evidence seeker admin permissions"""
    # Create admin permission for specific evidence seeker
    admin_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(admin_perm)
    db.commit()

    # Admin should have admin and reader access to their evidence seeker
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_READER, db
    )
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_ADMIN, db
    )

    # Admin should not have access to other evidence seekers
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id) + 1, UserRole.EVSE_READER, db
    )


def test_check_evidence_seeker_permission_evse_reader(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker, other_user: User
):
    """Test evidence seeker reader permissions"""
    # Use a seeker not owned by test_user to avoid owner-as-admin
    foreign_seeker = EvidenceSeeker(title="Foreign Seeker", created_by=other_user.id)
    db.add(foreign_seeker)
    db.commit()

    # Create reader permission for specific evidence seeker
    reader_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=foreign_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(reader_perm)
    db.commit()

    # Reader should have reader access but not admin access
    assert check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_READER, db
    )
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_ADMIN, db
    )

    # Reader should not have access to other evidence seekers
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(other_seeker)
    db.commit()
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(other_seeker.id), UserRole.EVSE_READER, db
    )


def test_check_evidence_seeker_permission_no_permission(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker, other_user: User
):
    """Test user without permissions has no access"""
    # User has no permissions and does not own this seeker
    foreign_seeker = EvidenceSeeker(title="Foreign Seeker", created_by=other_user.id)
    db.add(foreign_seeker)
    db.commit()
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_READER, db
    )
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_ADMIN, db
    )


def test_get_user_permissions(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test getting all permissions for a user"""
    # Create multiple permissions
    perm1 = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    # Create another seeker to attach second permission
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=test_user.id)
    db.add(other_seeker)
    db.commit()
    perm2 = Permission(
        user_id=test_user.id,
        evidence_seeker_id=other_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(perm1)
    db.add(perm2)
    db.commit()

    permissions = get_user_permissions(int(test_user.id), db)
    assert len(permissions) == 2
    role_counts = {p.role_value: int(p.evidence_seeker_id or 0) for p in permissions}
    assert role_counts[UserRole.EVSE_ADMIN] == int(test_evidence_seeker.id)
    assert role_counts[UserRole.EVSE_READER] == int(other_seeker.id)


def test_require_evidence_seeker_admin_success(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test require_evidence_seeker_admin dependency with valid permissions"""
    # Create admin permission
    admin_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(admin_perm)
    db.commit()

    # Should not raise exception
    result = require_evidence_seeker_admin(int(test_evidence_seeker.id), test_user, db)
    assert result == test_user


def test_require_evidence_seeker_admin_failure(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker, other_user: User
):
    """Test require_evidence_seeker_admin dependency with insufficient permissions"""
    # Use a seeker not owned by test_user and with no permissions
    foreign_seeker = EvidenceSeeker(title="Foreign Seeker", created_by=other_user.id)
    db.add(foreign_seeker)
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        require_evidence_seeker_admin(int(foreign_seeker.id), test_user, db)

    assert exc_info.value.status_code == 403
    assert "admin access required" in exc_info.value.detail


def test_require_evidence_seeker_reader_success(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test require_evidence_seeker_reader dependency with valid permissions"""
    # Create reader permission
    reader_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(reader_perm)
    db.commit()

    # Should not raise exception
    result = require_evidence_seeker_reader(int(test_evidence_seeker.id), test_user, db)
    assert result == test_user


def test_require_evidence_seeker_reader_failure(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker, other_user: User
):
    """Test require_evidence_seeker_reader dependency with insufficient permissions"""
    # Use a seeker not owned by test_user and with no permissions
    foreign_seeker = EvidenceSeeker(title="Foreign Seeker", created_by=other_user.id)
    db.add(foreign_seeker)
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        require_evidence_seeker_reader(int(foreign_seeker.id), test_user, db)

    assert exc_info.value.status_code == 403
    assert "read access required" in exc_info.value.detail


def test_require_platform_admin_success(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker
):
    """Test require_platform_admin dependency with platform admin permissions"""
    # Create platform admin permission
    platform_admin_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,  # associate with existing seeker
        role=UserRole.PLATFORM_ADMIN,
    )
    db.add(platform_admin_perm)
    db.commit()

    # Should not raise exception
    result = require_platform_admin(test_user, db)
    assert result == test_user


def test_require_platform_admin_failure(db: Session, test_user: User):
    """Test require_platform_admin dependency without platform admin permissions"""
    with pytest.raises(HTTPException) as exc_info:
        require_platform_admin(test_user, db)

    assert exc_info.value.status_code == 403
    assert "platform admin access required" in exc_info.value.detail


def test_role_hierarchy(
    db: Session, test_user: User, test_evidence_seeker: EvidenceSeeker, other_user: User
):
    """Test that role hierarchy works correctly (PLATFORM_ADMIN > EVSE_ADMIN > EVSE_READER)"""
    # Test platform admin has all access levels
    platform_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.PLATFORM_ADMIN,
    )
    db.add(platform_perm)
    db.commit()

    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_READER, db
    )
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_ADMIN, db
    )

    # Clean up and test admin hierarchy
    db.delete(platform_perm)
    admin_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=test_evidence_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(admin_perm)
    db.commit()

    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_READER, db
    )
    assert check_evidence_seeker_permission(
        int(test_user.id), int(test_evidence_seeker.id), UserRole.EVSE_ADMIN, db
    )

    # Clean up and test reader has only reader access (on a non-owned seeker)
    db.delete(admin_perm)
    foreign_seeker = EvidenceSeeker(title="Foreign Seeker", created_by=other_user.id)
    db.add(foreign_seeker)
    db.commit()
    reader_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=foreign_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(reader_perm)
    db.commit()

    assert check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_READER, db
    )
    assert not check_evidence_seeker_permission(
        int(test_user.id), int(foreign_seeker.id), UserRole.EVSE_ADMIN, db
    )
