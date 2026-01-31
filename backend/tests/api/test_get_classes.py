import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_classes_instructor_success(client, monkeypatch):
    # Arrange: Patch ClassService to return mock data
    mock_classes = [
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
    from app.services.classes.class_query_service import ClassService
    monkeypatch.setattr(ClassService, "get_classes_for_user", lambda self, user_id, user_type: mock_classes)

    # Act
    response = client.get(
        "/classes",
        headers={
            "x-user-id": str(uuid4()),
            "x-user-type": "instructor"
        }
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "classes" in data
    assert data["classes"][0]["course_code"] == "CSC4352"

def test_get_classes_student_success(client, monkeypatch):
    # Arrange: Patch ClassService to return mock data
    mock_classes = [
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
    from app.services.classes.class_query_service import ClassService
    monkeypatch.setattr(ClassService, "get_classes_for_user", lambda self, user_id, user_type: mock_classes)

    # Act
    response = client.get(
        "/classes",
        headers={
            "x-user-id": str(uuid4()),
            "x-user-type": "student"
        }
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "classes" in data
    assert data["classes"][0]["course_code"] == "MATH1738"

def test_get_classes_invalid_user_type(client):
    response = client.get(
        "/classes",
        headers={
            "x-user-id": str(uuid4()),
            "x-user-type": "admin"
        }
    )
    assert response.status_code == 400 or response.status_code == 403
