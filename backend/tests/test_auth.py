import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

DEFAULT_PASSWORD = "ValidPass123"


def register_user(
    client: TestClient, email: str, username: str, password: str = DEFAULT_PASSWORD
):
    """Helper to register a user and return the response."""
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )


def login_user(client: TestClient, username_or_email: str, password: str):
    """Helper to perform the FastAPI Users login flow."""
    return client.post(
        "/api/v1/auth/jwt/login",
        data={"username": username_or_email, "password": password},
    )


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_user_success(self, test_client: TestClient):
        """Test successful user registration"""
        response = register_user(test_client, "newuser@example.com", "newuser")

        assert response.status_code == 201
        data = response.json()
        # Default router returns the created user directly (not wrapped)
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        # camelCase serialization on fields
        assert data["isActive"] is True
        assert data["isVerified"] is False

    def test_register_user_invalid_email(self, test_client: TestClient):
        """Test registration with invalid email"""
        response = register_user(
            test_client, "invalid-email", "invaliduser", DEFAULT_PASSWORD
        )

        assert response.status_code == 422

    def test_register_user_weak_password(self, test_client: TestClient):
        """Test registration with weak password"""
        response = register_user(test_client, "test@example.com", "testuser", "123")

        assert response.status_code == 400

    def test_register_user_password_requires_letter(self, test_client: TestClient):
        """Password without digits should be rejected."""
        response = register_user(
            test_client,
            "letter-only@example.com",
            "letteronly",
            "onlyletters",
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Password must include at least one letter and one number."
        )

    def test_register_user_password_requires_number(self, test_client: TestClient):
        """Password without letters should be rejected."""
        response = register_user(
            test_client,
            "numbers-only@example.com",
            "numbersonly",
            "123456789",
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Password must include at least one letter and one number."
        )

    def test_register_user_duplicate_username(self, test_client: TestClient):
        """Usernames must be unique even if emails differ."""
        first = register_user(test_client, "dup@example.com", "dupuser")
        assert first.status_code == 201

        response = register_user(
            test_client, "another@example.com", "dupuser", DEFAULT_PASSWORD
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Username already taken"

    def test_login_user_success(self, test_client: TestClient):
        """Test successful user login"""
        # First register a user
        register_user(test_client, "loginuser@example.com", "loginuser")

        # Now try to login
        response = login_user(
            test_client,
            "loginuser@example.com",  # fastapi-users expects 'username'
            DEFAULT_PASSWORD,
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_user_invalid_credentials(self, test_client: TestClient):
        """Test login with invalid credentials"""
        response = login_user(
            test_client, "nonexistent@example.com", "wrongpassword"
        )

        assert response.status_code == 400

    def test_get_current_user_authenticated(
        self, test_client: TestClient, auth_headers
    ):
        """Test getting current user when authenticated"""
        response = test_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["username"] == "testuser"
        assert data["isActive"] is True

    def test_get_current_user_unauthenticated(self, test_client: TestClient):
        """Test getting current user when not authenticated"""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_resend_verification_requires_auth(self, test_client: TestClient):
        """Endpoint should reject unauthenticated requests."""
        response = test_client.post("/api/v1/auth/resend-verification")

        assert response.status_code == 401

    def test_resend_verification_for_unverified_user(self, test_client: TestClient):
        """Unverified users can request a new verification email."""
        register_user(test_client, "verifyme@example.com", "verifyme")
        login_response = login_user(
            test_client, "verifyme@example.com", DEFAULT_PASSWORD
        )
        token = login_response.json()["access_token"]

        response = test_client.post(
            "/api/v1/auth/resend-verification",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Verification email sent successfully"

    def test_logout(self, test_client: TestClient, auth_headers):
        """Test user logout"""
        response = test_client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"

    def test_auth_test_endpoint(self, test_client: TestClient):
        """Test auth test endpoint"""
        response = test_client.get("/api/v1/auth/test")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Authentication endpoints are working!"

    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == settings.version

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data


class TestAuthIntegration:
    """Integration tests for authentication"""

    @pytest.mark.integration
    def test_full_auth_flow(self, test_client: TestClient):
        """Test complete authentication flow"""
        # Register user
        register_response = register_user(
            test_client, "integration@example.com", "integration", "integration123"
        )
        assert register_response.status_code == 201

        # Login user
        login_response = login_user(
            test_client, "integration@example.com", "integration123"
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get current user
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "integration@example.com"

        # Logout
        logout_response = test_client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 200

    @pytest.mark.integration
    def test_duplicate_user_registration(self, test_client: TestClient):
        """Test registering user with existing email"""
        user_data = {
            "email": "duplicate@example.com",
            "username": "duplicate",
            "password": "password123",
        }

        # First registration should succeed
        response1 = test_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Second registration should fail
        response2 = test_client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
