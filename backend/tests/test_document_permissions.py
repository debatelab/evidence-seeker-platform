from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.onboarding_tokens import onboarding_token_service
from app.models.api_key import APIKey
from app.models.document import Document
from app.models.evidence_seeker import EvidenceSeeker
from app.models.evidence_seeker_settings import EvidenceSeekerSettings
from app.models.permission import Permission, UserRole
from app.models.user import User


def _configure_seeker(
    db: Session,
    seeker: EvidenceSeeker,
    *,
    state: str = "READY",
    missing: list[str] | None = None,
) -> None:
    """Attach a dummy Hugging Face key so guards allow operations."""
    api_key = APIKey(
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=seeker.uuid,
        encrypted_key="encrypted-test-key",
        key_hash="hash",
        provider="huggingface",
        name="default",
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    settings = EvidenceSeekerSettings(
        evidence_seeker_id=seeker.id,
        huggingface_api_key_id=api_key.id,
        embed_backend_type="huggingface",
        metadata_filters={},
        setup_mode="SIMPLE",
        configuration_state=state,
        missing_requirements=missing or [],
    )
    db.add(settings)
    db.commit()


def test_upload_document_requires_auth(client: TestClient):
    """Test that uploading documents requires authentication"""
    # Create a test file
    file_content = b"Test document content"
    file = BytesIO(file_content)
    file.name = "test.txt"

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "title": "Test Document",
            "description": "Test description",
            "evidence_seeker_uuid": "test-uuid",
        },
    )
    assert response.status_code == 401


def test_upload_document_requires_admin_permission(
    client: TestClient, test_user: User, db: Session, other_user: User
):
    """Test that uploading documents requires admin permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(other_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a test file
    file_content = b"Test document content"
    file = BytesIO(file_content)
    file.name = "test.txt"

    # Try to upload without permission
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "title": "Test Document",
            "description": "Test description",
            "evidence_seeker_uuid": str(other_seeker.uuid),
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_upload_document_success_with_permission(
    client: TestClient, test_user: User, db: Session
):
    """Test successful document upload with admin permission"""
    # Create an evidence seeker
    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()
    _configure_seeker(db, seeker)

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a test file
    file_content = b"Test document content"
    file = BytesIO(file_content)
    file.name = "test.txt"

    # Upload document (user owns the seeker so has admin permission)
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "title": "Test Document",
            "description": "Test description",
            "evidence_seeker_uuid": str(seeker.uuid),
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Document"
    assert data["description"] == "Test description"
    assert data["evidenceSeekerId"] == seeker.id


def test_upload_document_blocked_until_configured(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Uploading documents should fail with 409 when config incomplete."""
    seeker = EvidenceSeeker(title="Unconfigured", created_by=test_user.id)
    db.add(seeker)
    db.commit()

    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"Test document content"
    file = BytesIO(file_content)
    file.name = "test.txt"

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "title": "Test Document",
            "description": "Test description",
            "evidence_seeker_uuid": str(seeker.uuid),
        },
        headers=headers,
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["state"] in {"UNCONFIGURED", "MISSING_CREDENTIALS"}


def test_onboarding_token_allows_upload_before_ready(
    client: TestClient, test_user: User, db: Session
) -> None:
    """Uploading with a valid onboarding token bypasses the ready guard."""
    seeker = EvidenceSeeker(title="Wizard", created_by=test_user.id)
    db.add(seeker)
    db.commit()
    _configure_seeker(
        db,
        seeker,
        state="MISSING_DOCUMENTS",
        missing=["DOCUMENTS"],
    )

    onboarding_token = onboarding_token_service.issue_token(
        db=db,
        seeker=seeker,
        owner_user_id=test_user.id,
    )

    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Onboarding-Token": onboarding_token,
    }

    file_content = b"Wizard document"
    file = BytesIO(file_content)
    file.name = "wizard.txt"

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": (file.name, file, "text/plain")},
        data={
            "title": "Wizard attachment",
            "description": "Uploaded during onboarding",
            "evidence_seeker_uuid": str(seeker.uuid),
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["document"]["title"] == "Wizard attachment"


def test_invalid_onboarding_token_rejected(
    client: TestClient, test_user: User, db: Session
) -> None:
    """An invalid onboarding token should not bypass the guard."""
    seeker = EvidenceSeeker(title="InvalidToken", created_by=test_user.id)
    db.add(seeker)
    db.commit()
    _configure_seeker(
        db,
        seeker,
        state="MISSING_DOCUMENTS",
        missing=["DOCUMENTS"],
    )

    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Onboarding-Token": "not-a-real-token",
    }

    file_content = b"Wizard document"
    file = BytesIO(file_content)
    file.name = "wizard.txt"

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": (file.name, file, "text/plain")},
        data={
            "title": "Wizard attachment",
            "description": "Uploaded during onboarding",
            "evidence_seeker_uuid": str(seeker.uuid),
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_get_documents_requires_auth(client: TestClient):
    """Test that getting documents requires authentication"""
    response = client.get("/api/v1/documents/?evidence_seeker_uuid=test-uuid")
    assert response.status_code == 401


def test_get_documents_requires_reader_permission(
    client: TestClient, test_user: User, db: Session, other_user: User
):
    """Test that getting documents requires reader permission"""
    # Create an evidence seeker owned by someone else
    other_seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(other_seeker)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get documents without permission
    response = client.get(
        f"/api/v1/documents/?evidence_seeker_uuid={other_seeker.uuid}", headers=headers
    )
    assert response.status_code == 403


def test_get_documents_success_with_permission(
    client: TestClient, test_user: User, db: Session, other_user: User
):
    """Test successful document retrieval with reader permission"""
    # Create an evidence seeker and give user reader permission
    seeker = EvidenceSeeker(title="Test Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Create a document for the seeker
    document = Document(
        title="Test Document",
        description="Test description",
        file_path="/tmp/test.txt",
        original_filename="test.txt",
        file_size=100,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get documents with permission
    response = client.get(
        f"/api/v1/documents/?evidence_seeker_uuid={seeker.uuid}", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Document"


def test_download_document_requires_auth(client: TestClient):
    """Test that downloading documents requires authentication"""
    response = client.get("/api/v1/documents/test-uuid/download")
    assert response.status_code == 401


def test_download_document_requires_reader_permission(
    client: TestClient, test_user: User, db: Session, other_user: User
):
    """Test that downloading documents requires reader permission"""
    # Create an evidence seeker and document owned by someone else
    seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    document = Document(
        title="Test Document",
        description="Test description",
        file_path="/tmp/test.txt",
        original_filename="test.txt",
        file_size=100,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to download without permission
    response = client.get(
        f"/api/v1/documents/{document.uuid}/download", headers=headers
    )
    assert response.status_code == 403


def test_download_document_success_with_permission(
    client: TestClient, test_user: User, db: Session, tmp_path, other_user: User
):
    """Test successful document download with reader permission"""
    # Create an evidence seeker and give user reader permission
    seeker = EvidenceSeeker(title="Test Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_READER,
    )
    db.add(permission)
    db.commit()

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    # Create a document for the seeker
    document = Document(
        title="Test Document",
        description="Test description",
        file_path=str(test_file),
        original_filename="test.txt",
        file_size=12,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Download document with permission
    response = client.get(
        f"/api/v1/documents/{document.uuid}/download", headers=headers
    )
    assert response.status_code == 200
    # Some servers include a charset in the content-type for text files
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["content-disposition"] == 'attachment; filename="test.txt"'
    assert b"Test content" in response.content


def test_delete_document_requires_auth(client: TestClient):
    """Test that deleting documents requires authentication"""
    response = client.delete("/api/v1/documents/test-uuid")
    assert response.status_code == 401


def test_delete_document_requires_admin_permission(
    client: TestClient, test_user: User, db: Session, other_user: User
):
    """Test that deleting documents requires admin permission"""
    # Create an evidence seeker and document owned by someone else
    seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    document = Document(
        title="Test Document",
        description="Test description",
        file_path="/tmp/test.txt",
        original_filename="test.txt",
        file_size=100,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to delete without permission
    response = client.delete(f"/api/v1/documents/{document.uuid}", headers=headers)
    assert response.status_code == 403


def test_delete_document_success_with_permission(
    client: TestClient, test_user: User, db: Session, tmp_path, other_user: User
):
    """Test successful document deletion with admin permission"""
    # Create an evidence seeker and give user admin permission
    seeker = EvidenceSeeker(title="Test Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    permission = Permission(
        user_id=test_user.id,
        evidence_seeker_id=seeker.id,
        role=UserRole.EVSE_ADMIN,
    )
    db.add(permission)
    db.commit()

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    # Create a document for the seeker
    document = Document(
        title="Test Document",
        description="Test description",
        file_path=str(test_file),
        original_filename="test.txt",
        file_size=12,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
    db.commit()

    # Login
    login_response = client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Delete document with permission
    response = client.delete(f"/api/v1/documents/{document.uuid}", headers=headers)
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"]

    # Verify document is deleted from database
    from app.core.database import SessionLocal

    db_session = SessionLocal()
    deleted_doc = db_session.query(Document).filter(Document.id == document.id).first()
    db_session.close()
    assert deleted_doc is None


def test_platform_admin_has_full_document_access(
    client: TestClient, test_user: User, db: Session, tmp_path, other_user: User
):
    """Test that platform admins have full access to all documents"""
    # Create evidence seeker and document owned by someone else
    seeker = EvidenceSeeker(title="Other Seeker", created_by=other_user.id)
    db.add(seeker)
    db.commit()

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    document = Document(
        title="Test Document",
        description="Test description",
        file_path=str(test_file),
        original_filename="test.txt",
        file_size=12,
        mime_type="text/plain",
        evidence_seeker_id=seeker.id,
        evidence_seeker_uuid=str(seeker.uuid),
    )
    db.add(document)
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

    # Platform admin should be able to get documents
    response = client.get(
        f"/api/v1/documents/?evidence_seeker_uuid={seeker.uuid}", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    # Platform admin should be able to download
    response = client.get(
        f"/api/v1/documents/{document.uuid}/download", headers=headers
    )
    assert response.status_code == 200

    # Platform admin should be able to delete
    response = client.delete(f"/api/v1/documents/{document.uuid}", headers=headers)
    assert response.status_code == 200
