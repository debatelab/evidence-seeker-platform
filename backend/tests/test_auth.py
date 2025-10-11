import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_user_success(self, test_client: TestClient):
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "testpassword123",
        }

        response = test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        # Default router returns the created user directly (not wrapped)
        assert data["email"] == user_data["email"]
        # camelCase serialization on fields
        assert data["isActive"] is True
        assert data["isVerified"] is False

    def test_register_user_invalid_email(self, test_client: TestClient):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "username": "invaliduser",
            "password": "testpassword123",
        }

        response = test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422

    def test_register_user_weak_password(self, test_client: TestClient):
        """Test registration with weak password"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "123",
        }

        response = test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400

    def test_login_user_success(self, test_client: TestClient):
        """Test successful user login"""
        # First register a user
        user_data = {
            "email": "loginuser@example.com",
            "username": "loginuser",
            "password": "testpassword123",
        }
        test_client.post("/api/v1/auth/register", json=user_data)

        # Now try to login
        login_data = {
            "username": "loginuser@example.com",  # fastapi-users expects 'username'
            "password": "testpassword123",
        }

        response = test_client.post("/api/v1/auth/jwt/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_user_invalid_credentials(self, test_client: TestClient):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword",
        }

        response = test_client.post("/api/v1/auth/jwt/login", data=login_data)

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
        assert data["isActive"] is True

    def test_get_current_user_unauthenticated(self, test_client: TestClient):
        """Test getting current user when not authenticated"""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 401

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
        assert data["version"] == "1.0.0"

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
        user_data = {
            "email": "integration@example.com",
            "username": "integration",
            "password": "integration123",
        }
        register_response = test_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Login user
        login_data = {
            "username": "integration@example.com",
            "password": "integration123",
        }
        login_response = test_client.post("/api/v1/auth/jwt/login", data=login_data)
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
