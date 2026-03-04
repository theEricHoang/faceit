import pytest
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from app.main import app
from app.api.deps import get_current_user
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser
from app.services.classes.class_read_repository import ClassReadRepository, ClassReadError
from app.schemas.student import ClassEnrolledStudentsResponse, StudentEnrollmentItem

# ----------------------------------------------------------------------------
# Test data fixtures
# ----------------------------------------------------------------------------

TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_CLASS_ID = str(uuid4())

@pytest.fixture
def mock_students():
    return [
        {
            "id": str(uuid4()),
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
        },
        {
            "id": str(uuid4()),
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob.johnson@example.com",
        },
    ]

@pytest.fixture
def mock_instructor_classes():
    return [
        {"id": TEST_CLASS_ID},
    ]

# ----------------------------------------------------------------------------
# Success / authorization tests
# ----------------------------------------------------------------------------


def test_get_class_students_success(monkeypatch, mock_students, mock_instructor_classes):
    """Instructor who owns the class should see enrolled students."""
    # Arrange
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email="instructor@example.com",
        type=ProfileType.INSTRUCTOR,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # patch repository methods
    monkeypatch.setattr(
        ClassReadRepository,
        "get_classes_by_instructor",
        lambda self, instr_id: mock_instructor_classes,
    )
    monkeypatch.setattr(
        ClassReadRepository,
        "get_students_by_class",
        lambda self, cls_id: mock_students,
    )

    client = TestClient(app)
    response = client.get(f"/classes/{TEST_CLASS_ID}/students")

    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == TEST_CLASS_ID
    assert len(data["students"]) == 2
    assert data["students"][0]["email"] == "jane.smith@example.com"

    app.dependency_overrides.clear()


def test_get_class_students_forbidden_student(monkeypatch):
    """Students should not be able to query enrolled students."""
    mock_user = CurrentUser(
        user_id=UUID(TEST_USER_ID),
        email="student@example.com",
        type=ProfileType.STUDENT,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)
    response = client.get(f"/classes/{TEST_CLASS_ID}/students")
    assert response.status_code == 403
    assert "Only instructors" in response.json()["detail"]

    app.dependency_overrides.clear()
