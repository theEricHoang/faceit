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
TEST_STUDENT_EMAIL = "test.student@example.com"


# ============================================================================
# Success Tests
# ============================================================================

def test_list_open_classes_success(monkeypatch):
    """Authenticated user can fetch all open classes."""
    # Arrange: Mock authentication
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email=TEST_STUDENT_EMAIL,
        type=ProfileType.STUDENT,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock ClassService.get_all_classes
    from app.services.classes.class_query_service import ClassService
    mock_classes = [
        {
            "id": str(uuid4()),
            "course_code": "CSC1010",
            "course_name": "Intro to CS",
            "section": "10001",
            "term": "Fall 2025",
            "schedule": "M-W 9:00AM-10:00AM",
            "room": "Building A 101",
        },
        {
            "id": str(uuid4()),
            "course_code": "MATH1738",
            "course_name": "Calculus I",
            "section": "20002",
            "term": "Spring 2026",
            "schedule": "T-Th 10:00AM-11:15AM",
            "room": "Building B 202",
        },
    ]
    monkeypatch.setattr(
        ClassService,
        "get_all_classes",
        lambda self: mock_classes,
    )

    client = TestClient(app)

    # Act
    response = client.get("/classes/open")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "classes" in data
    assert len(data["classes"]) == 2
    assert data["classes"][0]["course_code"] == "CSC1010"
    assert data["classes"][1]["course_code"] == "MATH1738"

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Authorization Tests
# ============================================================================

def test_list_open_classes_unauthorized():
    """Request without authentication token returns 401."""
    # Arrange: Clear any auth overrides
    app.dependency_overrides.clear()

    client = TestClient(app)

    # Act
    response = client.get("/classes/open")

    # Assert
    assert response.status_code == 401

    # Cleanup
    app.dependency_overrides.clear()
