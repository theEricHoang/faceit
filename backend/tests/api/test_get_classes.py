import pytest
from fastapi.testclient import TestClient
from uuid import uuid4, UUID

from app.main import app
from app.api.deps import get_current_user
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser


# ============================================================================
# Test Data
# ============================================================================

TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_INSTRUCTOR_EMAIL = "test.instructor@example.com"
TEST_STUDENT_EMAIL = "test.student@example.com"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_instructor_classes():
    """Mock classes for an instructor."""
    return [
        {
            "id": str(uuid4()),
            "course_code": "CSC4352",
            "course_name": "Capstone II",
            "section": "19884",
            "term": "Spring 2026",
            "schedule": "M-W 9:00AM-10:00AM",
            "room": "Langdale Hall 400",
        }
    ]


@pytest.fixture
def mock_student_classes():
    """Mock classes for a student."""
    return [
        {
            "id": str(uuid4()),
            "course_code": "MATH1738",
            "course_name": "Calculus I",
            "section": "10001",
            "term": "Fall 2025",
            "schedule": "T-Th 10:00AM-11:15AM",
            "room": "Petit Science Center 200",
        }
    ]


# ============================================================================
# Success Tests
# ============================================================================

def test_get_classes_instructor_success(monkeypatch, mock_instructor_classes):
    """Instructor can successfully list their classes."""
    # Arrange: Mock authentication as instructor
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_INSTRUCTOR_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock ClassService
    from app.services.classes.class_query_service import ClassService
    monkeypatch.setattr(
        ClassService, 
        "get_classes_for_user", 
        lambda self, user_id, user_type: mock_instructor_classes
    )

    client = TestClient(app)

    # Act
    response = client.get("/classes")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "classes" in data
    assert len(data["classes"]) == 1
    assert data["classes"][0]["course_code"] == "CSC4352"
    assert data["classes"][0]["course_name"] == "Capstone II"

    # Cleanup
    app.dependency_overrides.clear()


def test_get_classes_student_success(monkeypatch, mock_student_classes):
    """Student can successfully list their enrolled classes."""
    # Arrange: Mock authentication as student
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_STUDENT_EMAIL,
        type=ProfileType.STUDENT,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock ClassService
    from app.services.classes.class_query_service import ClassService
    monkeypatch.setattr(
        ClassService, 
        "get_classes_for_user", 
        lambda self, user_id, user_type: mock_student_classes
    )

    client = TestClient(app)

    # Act
    response = client.get("/classes")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "classes" in data
    assert len(data["classes"]) == 1
    assert data["classes"][0]["course_code"] == "MATH1738"
    assert data["classes"][0]["course_name"] == "Calculus I"

    # Cleanup
    app.dependency_overrides.clear()


def test_get_classes_empty_list(monkeypatch):
    """User with no classes gets an empty list."""
    # Arrange
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_INSTRUCTOR_EMAIL,
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    from app.services.classes.class_query_service import ClassService
    monkeypatch.setattr(
        ClassService, 
        "get_classes_for_user", 
        lambda self, user_id, user_type: []
    )

    client = TestClient(app)

    # Act
    response = client.get("/classes")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["classes"] == []

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Authorization Tests
# ============================================================================

def test_get_classes_unauthorized_without_token():
    """Request without authentication token returns 401."""
    # Arrange: Clear any auth overrides
    app.dependency_overrides.clear()

    client = TestClient(app)

    # Act
    response = client.get("/classes")

    # Assert
    assert response.status_code == 401

    # Cleanup
    app.dependency_overrides.clear()
