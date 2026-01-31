import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app

def test_post_classes_success(monkeypatch):
    # Arrange: Patch ClassService.create_class to return mock data
    mock_class = {
        "id": str(uuid4()),
        "course_code": "CSC4352",
        "course_name": "Capstone II",
        "section": "19884",
        "term": "Spring 2026",
        "schedule": "M-W 9:00AM-10:00AM",
        "room": "Langdale Hall 400",
    }
    from app.services.classes.class_service import ClassService
    async def mock_create_class(self, **kwargs):
        return mock_class
    monkeypatch.setattr(ClassService, "create_class", mock_create_class)

    client = TestClient(app)
    payload = {
        "course_code": "CSC4352",
        "course_name": "Capstone II",
        "section": "19884",
        "term": "Spring 2026",
        "schedule": "M-W 9:00AM-10:00AM",
        "room": "Langdale Hall 400"
    }
    headers = {"x-instructor-id": str(uuid4())}

    # Act
    response = client.post("/classes", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["course_code"] == "CSC4352"
    assert data["course_name"] == "Capstone II"
