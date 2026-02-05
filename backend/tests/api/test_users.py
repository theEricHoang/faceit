"""Unit tests for users API routes."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.models.instructor import ProfileType
from tests.conftest import TEST_EMAIL, TEST_USER_ID


class TestGetMyProfileRoute:
    """Tests for GET /users/me/profile endpoint."""

    def test_get_my_profile_success_returns_student_number(self, authenticated_client: TestClient):
        """Profile returns names, type, email, and student_number."""
        with patch("app.api.routes.users.UserProfileService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_profile_names_and_type.return_value = {
                "first_name": "Alice",
                "last_name": "Smith",
                "type": ProfileType.STUDENT.value,
                "bio": "Computer Science Student",
            }
            mock_instance.get_student_number.return_value = "S12345"
            mock_instance.get_student_major.return_value = "Computer Science"

            response = authenticated_client.get("/users/me/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        assert data["email"] == TEST_EMAIL
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Smith"
        assert data["full_name"] == "Alice Smith"
        # Ensure renamed field is present
        assert data["student_number"] == "S12345"
        # New fields
        assert data["bio"] == "Computer Science Student"
        assert data["major"] == "Computer Science"

    def test_get_my_profile_not_found_returns_404(self, authenticated_client: TestClient):
        """If service raises, route returns 404."""
        from app.services.user_profile_service import UserProfileServiceError

        with patch("app.api.routes.users.UserProfileService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_profile_names_and_type.side_effect = UserProfileServiceError("Profile not found")

            response = authenticated_client.get("/users/me/profile")

        assert response.status_code == 404
        assert "Profile not found" in response.json()["detail"]


class TestChangePasswordRoute:
    """Tests for POST /users/me/change-password endpoint."""

    def test_change_password_success(self, authenticated_client: TestClient):
        with patch("app.api.routes.users.UserAccountService") as MockSvc:
            mock_instance = MockSvc.return_value
            mock_instance.change_password.return_value = None

            response = authenticated_client.post(
                "/users/me/change-password", json={"new_password": "newsecurepass123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Password changed successfully"

    def test_change_password_error_returns_400(self, authenticated_client: TestClient):
        from app.services.user_account_service import UserAccountServiceError

        with patch("app.api.routes.users.UserAccountService") as MockSvc:
            mock_instance = MockSvc.return_value
            mock_instance.change_password.side_effect = UserAccountServiceError("Invalid password policy")

            # Use a valid-length password to avoid 422 validation error
            response = authenticated_client.post(
                "/users/me/change-password", json={"new_password": "validpass123"}
            )

        assert response.status_code == 400
        assert "Invalid password policy" in response.json()["detail"]
