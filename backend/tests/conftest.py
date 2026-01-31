"""Shared test fixtures for auth testing."""

from typing import Any, Generator
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser


# ============================================================================
# Mock Response Classes
# ============================================================================


class MockUser:
    """Mock Supabase auth user."""

    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email


class MockSession:
    """Mock Supabase auth session."""

    def __init__(
        self,
        access_token: str = "mock-access-token",
        refresh_token: str = "mock-refresh-token",
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token


class MockAuthResponse:
    """Mock Supabase auth response."""

    def __init__(self, user: MockUser | None = None, session: MockSession | None = None):
        self.user = user
        self.session = session


class MockTableResponse:
    """Mock Supabase table query response."""

    def __init__(self, data: list[dict[str, Any]] | dict[str, Any] | None = None):
        self.data = data


# ============================================================================
# Sample Data
# ============================================================================

TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_EMAIL = "test.instructor@example.com"
TEST_PASSWORD = "securepassword123"


@pytest.fixture
def sample_signup_data() -> dict[str, Any]:
    """Sample instructor signup request data."""
    return {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "John",
        "last_name": "Doe",
        "bio": "Professor of Computer Science",
        "department": "Computer Science",
        "office_location": "Building A, Room 101",
    }


@pytest.fixture
def sample_login_data() -> dict[str, Any]:
    """Sample login request data."""
    return {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    }


@pytest.fixture
def sample_refresh_data() -> dict[str, Any]:
    """Sample token refresh request data."""
    return {
        "refresh_token": "mock-refresh-token",
    }


# ============================================================================
# Mock Supabase Client
# ============================================================================


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Create a fully mocked Supabase client with chainable methods."""
    client = MagicMock()

    # Setup chainable table methods for insert operations
    def create_table_chain(table_name: str) -> MagicMock:
        table = MagicMock()
        insert_chain = MagicMock()
        select_chain = MagicMock()

        # insert().execute() chain
        table.insert.return_value = insert_chain
        insert_chain.execute.return_value = MockTableResponse(data=[{"id": TEST_USER_ID}])

        # select().eq().single().execute() chain
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MockTableResponse(
            data={
                "first_name": "John",
                "last_name": "Doe",
                "type": "instructor",
            }
        )

        return table

    # Make client.table() return appropriate mock based on table name
    client.table.side_effect = lambda name: create_table_chain(name)

    # Setup auth methods
    client.auth.sign_up.return_value = MockAuthResponse(
        user=MockUser(TEST_USER_ID, TEST_EMAIL),
        session=MockSession(),
    )

    client.auth.sign_in_with_password.return_value = MockAuthResponse(
        user=MockUser(TEST_USER_ID, TEST_EMAIL),
        session=MockSession(),
    )

    client.auth.refresh_session.return_value = MockAuthResponse(
        user=MockUser(TEST_USER_ID, TEST_EMAIL),
        session=MockSession(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
        ),
    )

    client.auth.admin.delete_user.return_value = None

    return client


# ============================================================================
# FastAPI Test Client
# ============================================================================


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


# ============================================================================
# Auth Test Fixtures
# ============================================================================


@pytest.fixture
def mock_instructor_user() -> CurrentUser:
    """Mock authenticated instructor user."""
    return CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )


@pytest.fixture
def mock_student_user() -> CurrentUser:
    """Mock authenticated student user."""
    return CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email="test.student@example.com",
        type=ProfileType.STUDENT,
    )


@pytest.fixture
def authenticated_client(
    mock_instructor_user: CurrentUser,
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked instructor authentication."""
    app.dependency_overrides[get_current_user] = lambda: mock_instructor_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def student_authenticated_client(
    mock_student_user: CurrentUser,
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked student authentication."""
    app.dependency_overrides[get_current_user] = lambda: mock_student_user
    yield TestClient(app)
    app.dependency_overrides.clear()
