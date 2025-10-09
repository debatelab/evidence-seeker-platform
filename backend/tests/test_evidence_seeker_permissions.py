from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evidence_seeker import EvidenceSeeker
from app.models.permission import Permission, UserRole
from app.models.user import User


def test_create_evidence_seeker_requires_auth(client: TestClient) -> None:
    """Test that creating evidence seeker requires authentication"""
    response = client.post(
        "/api/v1/evidence-seekers/",
        json={"title": "Test Seeker", "description": "Test description"},
    )
    assert response.status_code == 401


def test_create_evidence_seeker_success(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test successful evidence seeker creation"""
    # Login first
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create evidence seeker
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/evidence-seekers/",
        json={"title": "Test Seeker", "description": "Test description"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Seeker"
    assert data["description"] == "Test description"
    assert data["createdBy"] == test_user.id


def test_get_evidence_seekers_requires_auth(client: TestClient) -> None:
    """Test that getting evidence seekers requires authentication"""
    response = client.get("/api/v1/evidence-seekers/")
    assert response.status_code == 401


def test_get_evidence_seekers_shows_owned_and_public(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that users can see evidence seekers they own or have access to"""
    # Create some evidence seekers
    seeker1 = EvidenceSeeker(title="Owned Seeker", created_by=test_user.id)
    seeker2 = EvidenceSeeker(title="Public Seeker", is_public=True, created_by=999)
    seeker3 = EvidenceSeeker(title="Private Seeker", is_public=False, created_by=999)

    db.add(seeker1)
    db.add(seeker2)
    db.add(seeker3)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get evidence seekers
    response = client.get("/api/v1/evidence-seekers/", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Should see owned and public seekers
    titles = {seeker["title"] for seeker in data}
    assert "Owned Seeker" in titles
    assert "Public Seeker" in titles
    assert "Private Seeker" not in titles


def test_get_evidence_seekers_with_permissions(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that users can see evidence seekers they have permissions for"""
    # Create a private evidence seeker
    private_seeker = EvidenceSeeker(
        title="Private Seeker", is_public=False, created_by=999
    )
    db.add(private_seeker)
    db.commit()

    # Give user reader permission
    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=private_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get evidence seekers
    response = client.get("/api/v1/evidence-seekers/", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Should see the private seeker due to permission
    titles = {seeker["title"] for seeker in data}
    assert "Private Seeker" in titles


def test_get_specific_evidence_seeker_requires_access(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that getting specific evidence seeker requires proper access"""
    # Create a private evidence seeker
    private_seeker = EvidenceSeeker(
        title="Private Seeker", is_public=False, created_by=999
    )
    db.add(private_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get private seeker without permission
    response = client.get(
        f"/api/v1/evidence-seekers/{private_seeker.id}", headers=headers
    )
    assert response.status_code == 404  # Should return 404 for security

    # Also try with UUID
    response = client.get(
        f"/api/v1/evidence-seekers/{private_seeker.uuid}", headers=headers
    )
    assert response.status_code == 404


def test_get_specific_evidence_seeker_with_permission(
    client: TestClient, test_user: User, db: Session
):
    """Test that users can access evidence seekers they have permission for"""
    # Create a private evidence seeker
    private_seeker = EvidenceSeeker(
        title="Private Seeker", is_public=False, created_by=999
    )
    db.add(private_seeker)
    db.commit()

    # Give user reader permission
    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=private_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get private seeker with permission
    response = client.get(
        f"/api/v1/evidence-seekers/{private_seeker.id}", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Private Seeker"

    # Also try with UUID
    response = client.get(
        f"/api/v1/evidence-seekers/{private_seeker.uuid}", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Private Seeker"


def test_update_evidence_seeker_requires_admin_permission(
    client: TestClient, test_user: User, db: Session
):
    """Test that updating evidence seeker requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=999)
    db.add(other_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to update without permission
    response = client.put(
        f"/api/v1/evidence-seekers/{other_seeker.id}",
        json={"title": "Updated Title"},
        headers=headers,
    )
    assert response.status_code == 403

    # Give admin permission
    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=other_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(permission)
    db.commit()

    # Try to update with permission
    response = client.put(
        f"/api/v1/evidence-seekers/{other_seeker.id}",
        json={"title": "Updated Title"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


def test_delete_evidence_seeker_requires_admin_permission(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that deleting evidence seeker requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=999)
    db.add(other_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to delete without permission
    response = client.delete(
        f"/api/v1/evidence-seekers/{other_seeker.id}", headers=headers
    )
    assert response.status_code == 403

    # Give admin permission
    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=other_seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(permission)
    db.commit()

    # Try to delete with permission
    response = client.delete(
        f"/api/v1/evidence-seekers/{other_seeker.id}", headers=headers
    )
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"]


def test_platform_admin_has_full_access(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that platform admins have access to all evidence seekers"""
    # Create evidence seekers owned by others
    seeker1 = EvidenceSeeker(title="Seeker 1", created_by=999)
    seeker2 = EvidenceSeeker(title="Seeker 2", created_by=999)
    db.add(seeker1)
    db.add(seeker2)
    db.commit()

    # Make user a platform admin
    platform_perm = Permission(
        user_id=test_user.id,
        evidence_seeker_id=1,  # Any ID works for platform admin
        role=UserRole.PLATFORM_ADMIN,
    )
    db.add(platform_perm)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Platform admin should see all evidence seekers
    response = client.get("/api/v1/evidence-seekers/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    titles = {seeker["title"] for seeker in data}
    assert "Seeker 1" in titles
    assert "Seeker 2" in titles

    # Platform admin should be able to update any seeker
    response = client.put(
        f"/api/v1/evidence-seekers/{seeker1.id}",
        json={"title": "Updated by Platform Admin"},
        headers=headers,
    )
    assert response.status_code == 200

    # Platform admin should be able to delete any seeker
    response = client.delete(f"/api/v1/evidence-seekers/{seeker2.id}", headers=headers)
    assert response.status_code == 200


# Tests for new user role assignment endpoints


def test_get_evidence_seeker_users_requires_admin_permission(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that getting evidence seeker users requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=999)
    db.add(other_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get users without permission
    response = client.get(
        f"/api/v1/permissions/evidence-seeker/{other_seeker.id}/users",
        headers=headers,
    )
    assert response.status_code == 403


def test_get_evidence_seeker_users_success(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test getting users for an evidence seeker with admin permission"""
    # Create an evidence seeker
    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()

    # Create another user
    other_user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(other_user)
    db.commit()

    # Give other user reader permission
    permission = Permission(
        user_id=other_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Login as admin
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get users
    response = client.get(
        f"/api/v1/permissions/evidence-seeker/{seeker.id}/users",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Should return users with roles (usernames only, no emails)
    assert len(data) == 1
    user_data = data[0]
    assert user_data["id"] == other_user.id
    assert user_data["username"] == other_user.username
    assert user_data["role"] == "EVSE_READER"
    assert "email" not in user_data  # GDPR compliance - no email exposure


def test_assign_evidence_seeker_role_requires_admin_permission(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that assigning roles requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=999)
    db.add(other_seeker)
    db.commit()

    # Create another user
    target_user = User(
        email="target@example.com",
        username="targetuser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(target_user)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to assign role without permission
    response = client.post(
        f"/api/v1/permissions/evidence-seeker/{other_seeker.id}/assign",
        json={"user_id": target_user.id, "role": "EVSE_READER"},
        headers=headers,
    )
    assert response.status_code == 403


def test_assign_evidence_seeker_role_success(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test successful role assignment"""
    # Create an evidence seeker
    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()

    # Create another user
    target_user = User(
        email="target@example.com",
        username="targetuser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(target_user)
    db.commit()

    # Login as admin
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Assign role
    response = client.post(
        f"/api/v1/permissions/evidence-seeker/{seeker.id}/assign",
        json={"user_id": target_user.id, "role": "EVSE_ADMIN"},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify permission was created
    permission = (
        db.query(Permission)
        .filter(
            Permission.user_id == target_user.id,
            Permission.evidence_seeker_id == seeker.id,
        )
        .first()
    )
    assert permission is not None
    assert permission.role == UserRole.EVSE_ADMIN


def test_assign_evidence_seeker_role_update_existing(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test updating existing role assignment"""
    # Create an evidence seeker
    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()

    # Create another user
    target_user = User(
        email="target@example.com",
        username="targetuser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(target_user)
    db.commit()

    # Create existing permission
    existing_perm = Permission(
        user_id=target_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(existing_perm)
    db.commit()

    # Login as admin
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update role
    response = client.post(
        f"/api/v1/permissions/evidence-seeker/{seeker.id}/assign",
        json={"user_id": target_user.id, "role": "EVSE_ADMIN"},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify permission was updated
    db.refresh(existing_perm)
    assert existing_perm.role == UserRole.EVSE_ADMIN


def test_remove_evidence_seeker_user_requires_admin_permission(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that removing users requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=999)
    db.add(other_seeker)
    db.commit()

    # Create another user
    target_user = User(
        email="target@example.com",
        username="targetuser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(target_user)
    db.commit()

    # Give target user permission
    permission = Permission(
        user_id=target_user.id,
        evidence_seeker_id=other_seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to remove user without permission
    response = client.delete(
        f"/api/v1/permissions/evidence-seeker/{other_seeker.id}/users/{target_user.id}",
        headers=headers,
    )
    assert response.status_code == 403


def test_remove_evidence_seeker_user_success(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test successful user removal"""
    # Create an evidence seeker
    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()

    # Create another user
    target_user = User(
        email="target@example.com",
        username="targetuser",
        hashed_password="hashed",
        is_active=True,
    )
    db.add(target_user)
    db.commit()

    # Give target user permission
    permission = Permission(
        user_id=target_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Login as admin
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Remove user
    response = client.delete(
        f"/api/v1/permissions/evidence-seeker/{seeker.id}/users/{target_user.id}",
        headers=headers,
    )
    assert response.status_code == 200

    # Verify permission was removed
    remaining_perm = (
        db.query(Permission)
        .filter(
            Permission.user_id == target_user.id,
            Permission.evidence_seeker_id == seeker.id,
        )
        .first()
    )
    assert remaining_perm is None


def test_user_search_for_assignment_requires_auth(client: TestClient) -> None:
    """Test that user search for assignment requires authentication"""
    response = client.get("/api/v1/users/search-for-assignment?q=test")
    assert response.status_code == 401


def test_user_search_for_assignment_success(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test successful user search for assignment"""
    # Create some test users
    user1 = User(
        email="alice@example.com",
        username="alice",
        hashed_password="hashed",
        is_active=True,
    )
    user2 = User(
        email="bob@example.com",
        username="bob",
        hashed_password="hashed",
        is_active=True,
    )
    user3 = User(
        email="charlie@example.com",
        username="charlie",
        hashed_password="hashed",
        is_active=False,  # Inactive user should not appear
    )
    db.add(user1)
    db.add(user2)
    db.add(user3)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Search for users
    response = client.get("/api/v1/users/search-for-assignment?q=ali", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Should return matching active users (usernames only, no emails)
    assert len(data) == 1
    user_data = data[0]
    assert user_data["id"] == user1.id
    assert user_data["username"] == "alice"
    assert "email" not in user_data  # GDPR compliance

    # Search should work for email too
    response = client.get("/api/v1/users/search-for-assignment?q=bob@", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "bob"


def test_user_search_for_assignment_minimum_length(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Test that user search requires minimum query length"""
    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Search with too short query
    response = client.get("/api/v1/users/search-for-assignment?q=a", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Should return empty array for short queries

    # Empty query
    response = client.get("/api/v1/users/search-for-assignment?q=", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
