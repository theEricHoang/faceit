"""Unit tests for auth dependencies."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import jwt as pyjwt

from app.api.deps import get_current_user, require_instructor, require_student
from app.core.config import get_settings
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser
from tests.conftest import TEST_EMAIL, TEST_USER_ID
import app.api.deps as deps_module

# Generate a test ES256 key pair for testing
_test_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
_test_public_key = _test_private_key.public_key()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set test environment variables, clear caches, and mock JWKS client."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-for-unit-tests")
    
    # Clear the cached settings and JWKS client
    get_settings.cache_clear()
    deps_module._jwks_client = None
    
    yield
    
    get_settings.cache_clear()
    deps_module._jwks_client = None


@pytest.fixture
def mock_jwks_client():
    """Mock the JWKS client to return our test public key."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = _test_public_key
    
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    
    with patch("app.api.deps.get_jwks_client", return_value=mock_client):
        yield mock_client


# ============================================================================
# Test Helpers
# ============================================================================


def create_test_token(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    user_type: str | None = "instructor",
    expired: bool = False,
) -> str:
    """Create a test JWT token signed with ES256."""
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

    return pyjwt.encode(payload, _test_private_key, algorithm="ES256")


class MockCredentials(HTTPAuthorizationCredentials):
    """Mock HTTPAuthorizationCredentials."""

    def __init__(self, token: str):
        super().__init__(scheme="Bearer", credentials=token)


# ============================================================================
# get_current_user Tests
# ============================================================================


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_instructor_token(self, mock_jwks_client):
        """Test valid token returns CurrentUser with instructor type."""
        token = create_test_token(user_type="instructor")
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.user_id == UUID(TEST_USER_ID)
        assert user.email == TEST_EMAIL
        assert user.type == ProfileType.INSTRUCTOR

    @pytest.mark.asyncio
    async def test_valid_student_token(self, mock_jwks_client):
        """Test valid token returns CurrentUser with student type."""
        token = create_test_token(user_type="student")
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.user_id == UUID(TEST_USER_ID)
        assert user.email == TEST_EMAIL
        assert user.type == ProfileType.STUDENT

    @pytest.mark.asyncio
    async def test_missing_user_type_defaults_to_student(self, mock_jwks_client):
        """Test token without user_type defaults to student."""
        token = create_test_token(user_type=None)
        credentials = MockCredentials(token)

        user = await get_current_user(credentials)

        assert user.type == ProfileType.STUDENT

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, mock_jwks_client):
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
    async def test_wrong_secret_returns_401(self, mock_jwks_client):
        """Test token signed with wrong key raises 401."""
        # Generate a different key pair
        wrong_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        
        payload = {
            "sub": TEST_USER_ID,
            "email": TEST_EMAIL,
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # Sign with the wrong key
        token = pyjwt.encode(payload, wrong_private_key, algorithm="ES256")
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
