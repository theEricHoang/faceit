"""Unit tests for auth API routes."""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.models.instructor import ProfileType
from app.schemas.user import (
    InstructorSignupResponse,
    LoginResponse,
    RefreshResponse,
)
from app.services.auth_service import LoginError, RefreshError, SignupError
from tests.conftest import TEST_EMAIL, TEST_USER_ID


# ============================================================================
# POST /auth/signup/instructor Tests
# ============================================================================


class TestSignupInstructorRoute:
    """Tests for POST /auth/signup/instructor endpoint."""

    def test_signup_instructor_success(
        self, test_client: TestClient, sample_signup_data: dict
    ):
        """Test successful signup returns 201 with user data and tokens."""
        mock_response = InstructorSignupResponse(
            access_token="mock-access-token",
            refresh_token="mock-refresh-token",
            token_type="bearer",
            user_id=UUID(TEST_USER_ID),
            email=TEST_EMAIL,
            first_name=sample_signup_data["first_name"],
            last_name=sample_signup_data["last_name"],
            bio=sample_signup_data["bio"],
            type=ProfileType.INSTRUCTOR,
            department=sample_signup_data["department"],
            office_location=sample_signup_data["office_location"],
        )

        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.signup_instructor = AsyncMock(return_value=mock_response)

            response = test_client.post(
                "/auth/signup/instructor",
                json=sample_signup_data,
            )

        assert response.status_code == 201
        data = response.json()
        # Verify auth tokens
        assert data["access_token"] == "mock-access-token"
        assert data["refresh_token"] == "mock-refresh-token"
        assert data["token_type"] == "bearer"
        # Verify user data
        assert data["user_id"] == TEST_USER_ID
        assert data["email"] == TEST_EMAIL
        assert data["first_name"] == sample_signup_data["first_name"]
        assert data["last_name"] == sample_signup_data["last_name"]
        assert data["type"] == "instructor"

    def test_signup_instructor_error_returns_400(
        self, test_client: TestClient, sample_signup_data: dict
    ):
        """Test signup error returns 400 with error message."""
        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.signup_instructor = AsyncMock(
                side_effect=SignupError("Email already registered")
            )

            response = test_client.post(
                "/auth/signup/instructor",
                json=sample_signup_data,
            )

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


# ============================================================================
# POST /auth/login Tests
# ============================================================================


class TestLoginRoute:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, test_client: TestClient, sample_login_data: dict):
        """Test successful login returns 200 with tokens and profile."""
        mock_response = LoginResponse(
            access_token="mock-access-token",
            refresh_token="mock-refresh-token",
            token_type="bearer",
            user_id=UUID(TEST_USER_ID),
            email=TEST_EMAIL,
            first_name="John",
            last_name="Doe",
            type=ProfileType.INSTRUCTOR,
        )

        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.login = AsyncMock(return_value=mock_response)

            response = test_client.post(
                "/auth/login",
                json=sample_login_data,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock-access-token"
        assert data["refresh_token"] == "mock-refresh-token"
        assert data["token_type"] == "bearer"
        assert data["user_id"] == TEST_USER_ID
        assert data["email"] == TEST_EMAIL
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["type"] == "instructor"

    def test_login_invalid_credentials_returns_401(
        self, test_client: TestClient, sample_login_data: dict
    ):
        """Test invalid credentials returns 401."""
        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.login = AsyncMock(
                side_effect=LoginError("Invalid email or password")
            )

            response = test_client.post(
                "/auth/login",
                json=sample_login_data,
            )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_profile_not_found_returns_401(
        self, test_client: TestClient, sample_login_data: dict
    ):
        """Test missing profile returns 401."""
        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.login = AsyncMock(
                side_effect=LoginError("User profile not found")
            )

            response = test_client.post(
                "/auth/login",
                json=sample_login_data,
            )

        assert response.status_code == 401
        assert "User profile not found" in response.json()["detail"]


# ============================================================================
# POST /auth/refresh Tests
# ============================================================================


class TestRefreshRoute:
    """Tests for POST /auth/refresh endpoint."""

    def test_refresh_success(self, test_client: TestClient, sample_refresh_data: dict):
        """Test successful refresh returns 200 with new tokens."""
        mock_response = RefreshResponse(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            token_type="bearer",
        )

        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.refresh_token = AsyncMock(return_value=mock_response)

            response = test_client.post(
                "/auth/refresh",
                json=sample_refresh_data,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access-token"
        assert data["refresh_token"] == "new-refresh-token"
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token_returns_401(
        self, test_client: TestClient, sample_refresh_data: dict
    ):
        """Test invalid refresh token returns 401."""
        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.refresh_token = AsyncMock(
                side_effect=RefreshError("Failed to refresh token")
            )

            response = test_client.post(
                "/auth/refresh",
                json=sample_refresh_data,
            )

        assert response.status_code == 401
        assert "Failed to refresh token" in response.json()["detail"]

    def test_refresh_expired_token_returns_401(
        self, test_client: TestClient, sample_refresh_data: dict
    ):
        """Test expired refresh token returns 401."""
        with patch(
            "app.api.routes.auth.AuthService"
        ) as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.refresh_token = AsyncMock(
                side_effect=RefreshError("Token refresh failed: Token expired")
            )

            response = test_client.post(
                "/auth/refresh",
                json=sample_refresh_data,
            )

        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]
