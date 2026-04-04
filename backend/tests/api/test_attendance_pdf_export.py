"""Tests for GET /classes/{class_id}/attendance/sessions/{session_id}/pdf."""

import uuid

import pytest
from fastapi import status

from app.api.deps import get_attendance_service, get_query_service


STUB_SESSION_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STUB_CLASS_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class FakeQueryService:
    def __init__(self, has_access: bool):
        self.has_access = has_access

    def instructor_has_class(self, instructor_id, class_id):
        return self.has_access

    def get_class_details(self, class_id):
        return {
            "id": str(class_id),
            "course_code": "CS101",
            "course_name": "Intro to Computing",
            "section": "A",
            "schedule": "Mon/Wed 10:00 AM",
            "room": "Room 12",
            "instructor_name": "Dr. Ada Lovelace",
        }


class FakeAttendanceService:
    def get_session_report(self, session_id, class_id):
        return {
            "session_id": str(session_id),
            "class_id": str(class_id),
            "created_at": "2026-03-06T10:00:00Z",
            "present_students": [
                {
                    "student_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "confidence": 0.94,
                },
            ],
            "unknown_count": 1,
        }

    def build_session_report_pdf(self, report, class_details=None):
        return b"%PDF-1.4\nFAKE"


@pytest.fixture(autouse=True)
def clear_overrides():
    from app.main import app

    yield
    app.dependency_overrides.clear()


def _apply_overrides(has_access=True):
    from app.main import app

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(has_access)
    app.dependency_overrides[get_attendance_service] = lambda: FakeAttendanceService()


def test_instructor_can_download_session_report_pdf(authenticated_client, mock_instructor_user):
    _apply_overrides(has_access=True)

    response = authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}/pdf"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"].lower()
    assert response.content.startswith(b"%PDF")


def test_class_not_owned_returns_404(authenticated_client):
    _apply_overrides(has_access=False)

    response = authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}/pdf"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Class not found"


def test_student_forbidden(student_authenticated_client):
    response = student_authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}/pdf"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Instructor access required"


def test_unauthenticated_returns_401(test_client):
    response = test_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}/pdf"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED