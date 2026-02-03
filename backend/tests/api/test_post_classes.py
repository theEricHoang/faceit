import pytest
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.api.deps import get_current_user
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser
from app.services.classes.class_service import ClassService, CreateClassError


# ============================================================================
# Test Data
# ============================================================================

TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_EMAIL = "test.instructor@example.com"


@pytest.fixture
def valid_class_payload():
    """Valid class creation payload."""
    return {
        "course_code": "CSC4352",
        "course_name": "Capstone II",
        "section": "19884",
        "term": "Spring 2026",
        "schedule": "M-W 9:00AM-10:00AM",
        "room": "Langdale Hall 400"
    }


@pytest.fixture
def mock_created_class():
    """Mock response from ClassService.create_class."""
    return {
        "id": str(uuid4()),
        "instructor_id": TEST_USER_ID,
        "course_code": "CSC4352",
        "course_name": "Capstone II",
        "section": "19884",
        "term": "Spring 2026",
        "schedule": "M-W 9:00AM-10:00AM",
        "room": "Langdale Hall 400",
    }


# ============================================================================
# Success Tests
# ============================================================================

def test_create_class_success_as_instructor(monkeypatch, valid_class_payload, mock_created_class):
    """Instructor can successfully create a class."""
    # Arrange: Mock authentication as instructor
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock ClassService.create_class
    async def mock_create_class(self, **kwargs):
        return mock_created_class
    monkeypatch.setattr(ClassService, "create_class", mock_create_class)

    client = TestClient(app)

    # Act
    response = client.post("/classes", json=valid_class_payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["course_code"] == "CSC4352"
    assert data["course_name"] == "Capstone II"
    assert data["section"] == "19884"
    assert data["term"] == "Spring 2026"
    assert "class_id" in data

    # Cleanup
    app.dependency_overrides.clear()


def test_create_class_without_optional_room(monkeypatch):
    """Class can be created without optional room field."""
    # Arrange
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_class = {
        "id": str(uuid4()),
        "course_code": "CSC101",
        "course_name": "Intro to CS",
        "section": "001",
        "term": "Fall 2026",
        "schedule": "T-Th 2:00PM-3:30PM",
        "room": None,
    }

    async def mock_create_class(self, **kwargs):
        return mock_class
    monkeypatch.setattr(ClassService, "create_class", mock_create_class)

    client = TestClient(app)
    payload = {
        "course_code": "CSC101",
        "course_name": "Intro to CS",
        "section": "001",
        "term": "Fall 2026",
        "schedule": "T-Th 2:00PM-3:30PM",
    }

    # Act
    response = client.post("/classes", json=payload)

    # Assert
    assert response.status_code == 200
    app.dependency_overrides.clear()


# ============================================================================
# Authorization Tests
# ============================================================================

def test_create_class_forbidden_for_student(valid_class_payload):
    """Students cannot create classes."""
    # Arrange: Mock authentication as student
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email="student@example.com",
        type=ProfileType.STUDENT,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)

    # Act
    response = client.post("/classes", json=valid_class_payload)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Only instructors can create classes"

    # Cleanup
    app.dependency_overrides.clear()


def test_create_class_unauthorized_without_token(valid_class_payload):
    """Request without authentication token returns 401."""
    # Arrange: Clear any auth overrides
    app.dependency_overrides.clear()

    client = TestClient(app)

    # Act
    response = client.post("/classes", json=valid_class_payload)

    # Assert
    assert response.status_code == 401  # HTTPBearer returns 401 when no token

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Validation Tests
# ============================================================================

def test_create_class_missing_required_fields():
    """Request with missing required fields returns 422."""
    # Arrange
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)
    payload = {
        "course_code": "CSC4352",
        # Missing course_name, section, term, schedule
    }

    # Act
    response = client.post("/classes", json=payload)

    # Assert
    assert response.status_code == 422

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_create_class_service_error(monkeypatch, valid_class_payload):
    """Database error returns 500."""
    # Arrange
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async def mock_create_class_error(self, **kwargs):
        raise CreateClassError("Database connection failed")
    monkeypatch.setattr(ClassService, "create_class", mock_create_class_error)

    client = TestClient(app)

    # Act
    response = client.post("/classes", json=valid_class_payload)

    # Assert
    assert response.status_code == 500
    assert "Database connection failed" in response.json()["detail"]

    # Cleanup
    app.dependency_overrides.clear()
