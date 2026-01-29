"""Unit tests for AuthService."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.models.instructor import ProfileType
from app.schemas.user import (
    InstructorSignupRequest,
    LoginRequest,
    RefreshRequest,
)
from app.services.auth_service import (
    AuthService,
    LoginError,
    RefreshError,
    SignupError,
)
from tests.conftest import (
    MockAuthResponse,
    MockSession,
    MockTableResponse,
    MockUser,
    TEST_EMAIL,
    TEST_USER_ID,
)


# ============================================================================
# signup_instructor Tests
# ============================================================================


class TestSignupInstructor:
    """Tests for AuthService.signup_instructor()."""

    @pytest.mark.asyncio
    async def test_signup_instructor_success(
        self, mock_supabase_client: MagicMock, sample_signup_data: dict
    ):
        """Test successful instructor signup creates all records."""
        auth_service = AuthService(client=mock_supabase_client)
        request = InstructorSignupRequest(**sample_signup_data)

        result = await auth_service.signup_instructor(request)

        # Verify auth user was created
        mock_supabase_client.auth.sign_up.assert_called_once_with(
            {"email": TEST_EMAIL, "password": sample_signup_data["password"]}
        )

        # Verify response data
        assert result.user_id == UUID(TEST_USER_ID)
        assert result.email == TEST_EMAIL
        assert result.first_name == sample_signup_data["first_name"]
        assert result.last_name == sample_signup_data["last_name"]
        assert result.bio == sample_signup_data["bio"]
        assert result.type == ProfileType.INSTRUCTOR
        assert result.department == sample_signup_data["department"]
        assert result.office_location == sample_signup_data["office_location"]

    @pytest.mark.asyncio
    async def test_signup_instructor_auth_failure(
        self, mock_supabase_client: MagicMock, sample_signup_data: dict
    ):
        """Test signup fails gracefully when auth user creation fails."""
        # Configure auth to return no user
        mock_supabase_client.auth.sign_up.return_value = MockAuthResponse(
            user=None, session=None
        )

        auth_service = AuthService(client=mock_supabase_client)
        request = InstructorSignupRequest(**sample_signup_data)

        with pytest.raises(SignupError, match="Failed to create auth user"):
            await auth_service.signup_instructor(request)

        # Verify no cleanup was attempted (no user was created)
        mock_supabase_client.auth.admin.delete_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_signup_instructor_profile_failure_triggers_rollback(
        self, mock_supabase_client: MagicMock, sample_signup_data: dict
    ):
        """Test that profile insert failure triggers auth user deletion."""
        # Configure profile insert to fail
        profiles_table = MagicMock()
        profiles_table.insert.return_value.execute.return_value = MockTableResponse(
            data=None
        )

        instructors_table = MagicMock()
        instructors_table.insert.return_value.execute.return_value = MockTableResponse(
            data=[{"id": TEST_USER_ID}]
        )

        def table_router(name: str) -> MagicMock:
            if name == "profiles":
                return profiles_table
            return instructors_table

        mock_supabase_client.table.side_effect = table_router

        auth_service = AuthService(client=mock_supabase_client)
        request = InstructorSignupRequest(**sample_signup_data)

        with pytest.raises(SignupError, match="Failed to create profile record"):
            await auth_service.signup_instructor(request)

        # Verify auth user was deleted for rollback
        mock_supabase_client.auth.admin.delete_user.assert_called_once_with(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_signup_instructor_instructor_failure_triggers_rollback(
        self, mock_supabase_client: MagicMock, sample_signup_data: dict
    ):
        """Test that instructor insert failure triggers auth user deletion."""
        # Configure instructor insert to fail
        profiles_table = MagicMock()
        profiles_table.insert.return_value.execute.return_value = MockTableResponse(
            data=[{"id": TEST_USER_ID}]
        )

        instructors_table = MagicMock()
        instructors_table.insert.return_value.execute.return_value = MockTableResponse(
            data=None
        )

        def table_router(name: str) -> MagicMock:
            if name == "profiles":
                return profiles_table
            return instructors_table

        mock_supabase_client.table.side_effect = table_router

        auth_service = AuthService(client=mock_supabase_client)
        request = InstructorSignupRequest(**sample_signup_data)

        with pytest.raises(SignupError, match="Failed to create instructor record"):
            await auth_service.signup_instructor(request)

        # Verify auth user was deleted for rollback
        mock_supabase_client.auth.admin.delete_user.assert_called_once_with(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_signup_instructor_unexpected_error_triggers_rollback(
        self, mock_supabase_client: MagicMock, sample_signup_data: dict
    ):
        """Test that unexpected exceptions still trigger rollback."""
        # Configure table insert to raise an unexpected exception
        mock_supabase_client.table.side_effect = Exception("Database connection lost")

        auth_service = AuthService(client=mock_supabase_client)
        request = InstructorSignupRequest(**sample_signup_data)

        with pytest.raises(SignupError, match="Signup failed"):
            await auth_service.signup_instructor(request)

        # Verify auth user was deleted for rollback
        mock_supabase_client.auth.admin.delete_user.assert_called_once_with(TEST_USER_ID)


# ============================================================================
# login Tests
# ============================================================================


class TestLogin:
    """Tests for AuthService.login()."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, mock_supabase_client: MagicMock, sample_login_data: dict
    ):
        """Test successful login returns tokens and profile data."""
        auth_service = AuthService(client=mock_supabase_client)
        request = LoginRequest(**sample_login_data)

        result = await auth_service.login(request)

        # Verify auth was called
        mock_supabase_client.auth.sign_in_with_password.assert_called_once_with(
            {"email": TEST_EMAIL, "password": sample_login_data["password"]}
        )

        # Verify response data
        assert result.access_token == "mock-access-token"
        assert result.refresh_token == "mock-refresh-token"
        assert result.token_type == "bearer"
        assert result.user_id == UUID(TEST_USER_ID)
        assert result.email == TEST_EMAIL
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.type == ProfileType.INSTRUCTOR

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(
        self, mock_supabase_client: MagicMock, sample_login_data: dict
    ):
        """Test login fails with invalid credentials."""
        # Configure auth to return no user/session
        mock_supabase_client.auth.sign_in_with_password.return_value = MockAuthResponse(
            user=None, session=None
        )

        auth_service = AuthService(client=mock_supabase_client)
        request = LoginRequest(**sample_login_data)

        with pytest.raises(LoginError, match="Invalid email or password"):
            await auth_service.login(request)

    @pytest.mark.asyncio
    async def test_login_profile_not_found(
        self, mock_supabase_client: MagicMock, sample_login_data: dict
    ):
        """Test login fails when user has no profile."""
        # Configure profile query to return no data
        profiles_table = MagicMock()
        select_chain = MagicMock()
        profiles_table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MockTableResponse(data=None)

        mock_supabase_client.table.side_effect = lambda name: profiles_table

        auth_service = AuthService(client=mock_supabase_client)
        request = LoginRequest(**sample_login_data)

        with pytest.raises(LoginError, match="User profile not found"):
            await auth_service.login(request)

    @pytest.mark.asyncio
    async def test_login_auth_exception(
        self, mock_supabase_client: MagicMock, sample_login_data: dict
    ):
        """Test login handles auth exceptions gracefully."""
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception(
            "Auth service unavailable"
        )

        auth_service = AuthService(client=mock_supabase_client)
        request = LoginRequest(**sample_login_data)

        with pytest.raises(LoginError, match="Login failed"):
            await auth_service.login(request)


# ============================================================================
# refresh_token Tests
# ============================================================================


class TestRefreshToken:
    """Tests for AuthService.refresh_token()."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, mock_supabase_client: MagicMock, sample_refresh_data: dict
    ):
        """Test successful token refresh returns new tokens."""
        auth_service = AuthService(client=mock_supabase_client)
        request = RefreshRequest(**sample_refresh_data)

        result = await auth_service.refresh_token(request)

        # Verify refresh was called
        mock_supabase_client.auth.refresh_session.assert_called_once_with(
            sample_refresh_data["refresh_token"]
        )

        # Verify response data
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(
        self, mock_supabase_client: MagicMock, sample_refresh_data: dict
    ):
        """Test refresh fails with invalid token."""
        # Configure refresh to return no session
        mock_supabase_client.auth.refresh_session.return_value = MockAuthResponse(
            user=None, session=None
        )

        auth_service = AuthService(client=mock_supabase_client)
        request = RefreshRequest(**sample_refresh_data)

        with pytest.raises(RefreshError, match="Failed to refresh token"):
            await auth_service.refresh_token(request)

    @pytest.mark.asyncio
    async def test_refresh_token_exception(
        self, mock_supabase_client: MagicMock, sample_refresh_data: dict
    ):
        """Test refresh handles exceptions gracefully."""
        mock_supabase_client.auth.refresh_session.side_effect = Exception(
            "Token expired"
        )

        auth_service = AuthService(client=mock_supabase_client)
        request = RefreshRequest(**sample_refresh_data)

        with pytest.raises(RefreshError, match="Token refresh failed"):
            await auth_service.refresh_token(request)
