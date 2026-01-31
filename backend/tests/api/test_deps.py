"""Unit tests for auth dependencies."""

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from jose import jwt

from app.api.deps import get_current_user, require_instructor, require_student
from app.core.config import get_settings
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser
from tests.conftest import TEST_EMAIL, TEST_USER_ID

# Test JWT secret - set in environment for tests
TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests"


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set test environment variables and clear settings cache."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    # Clear the cached settings so it picks up new env var
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ============================================================================
# Test Helpers
# ============================================================================


def create_test_token(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    user_type: str | None = "instructor",
    expired: bool = False,
) -> str:
    """Create a test JWT token."""
    exp = datetime.now(timezone.utc) + (
        timedelta(hours=-1) if expired else timedelta(hours=1)
    )

    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }

    if user_type:
        payload["user_metadata"] = {"type": user_type}

    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


class MockCredentials:
    """Mock HTTPAuthorizationCredentials."""

    def __init__(self, token: str):
        self.credentials = token


# ============================================================================
# get_current_user Tests
# ============================================================================


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_instructor_token(self):
        """Test valid token returns CurrentUser with instructor type."""
        token = create_test_token(user_type="instructor")
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.user_id == UUID(TEST_USER_ID)
        assert user.email == TEST_EMAIL
        assert user.type == ProfileType.INSTRUCTOR

    @pytest.mark.asyncio
    async def test_valid_student_token(self):
        """Test valid token returns CurrentUser with student type."""
        token = create_test_token(user_type="student")
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.user_id == UUID(TEST_USER_ID)
        assert user.email == TEST_EMAIL
        assert user.type == ProfileType.STUDENT

    @pytest.mark.asyncio
    async def test_missing_user_type_defaults_to_student(self):
        """Test token without user_type defaults to student."""
        token = create_test_token(user_type=None)
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.type == ProfileType.STUDENT

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self):
        """Test expired token raises 401."""
        token = create_test_token(expired=True)
        credentials = MockCredentials(token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """Test invalid token raises 401."""
        credentials = MockCredentials("invalid-token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_wrong_secret_returns_401(self):
        """Test token signed with wrong secret raises 401."""
        payload = {
            "sub": TEST_USER_ID,
            "email": TEST_EMAIL,
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        credentials = MockCredentials(token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401


# ============================================================================
# require_instructor Tests
# ============================================================================


class TestRequireInstructor:
    """Tests for require_instructor dependency."""

    @pytest.mark.asyncio
    async def test_instructor_allowed(self, mock_instructor_user: CurrentUser):
        """Test instructor user passes through."""
        result = await require_instructor(mock_instructor_user)

        assert result == mock_instructor_user
        assert result.type == ProfileType.INSTRUCTOR

    @pytest.mark.asyncio
    async def test_student_forbidden(self, mock_student_user: CurrentUser):
        """Test student user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            await require_instructor(mock_student_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Instructor access required"


# ============================================================================
# require_student Tests
# ============================================================================


class TestRequireStudent:
    """Tests for require_student dependency."""

    @pytest.mark.asyncio
    async def test_student_allowed(self, mock_student_user: CurrentUser):
        """Test student user passes through."""
        result = await require_student(mock_student_user)

        assert result == mock_student_user
        assert result.type == ProfileType.STUDENT

    @pytest.mark.asyncio
    async def test_instructor_forbidden(self, mock_instructor_user: CurrentUser):
        """Test instructor user raises 403."""
        with pytest.raises(HTTPException) as exc_info:
            await require_student(mock_instructor_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Student access required"
