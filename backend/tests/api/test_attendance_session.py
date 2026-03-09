"""Tests for GET /classes/{class_id}/attendance/sessions/{session_id}."""

import uuid

import pytest
from fastapi import status

from app.api.routes.attendance import get_attendance_service, get_query_service


# ---------------------------------------------------------------------------
# Fake service doubles
# ---------------------------------------------------------------------------

STUB_SESSION_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STUB_CLASS_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
STUB_STUDENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class FakeQueryService:
    """Configurable stub for ClassQueryService."""

    def __init__(self, has_access: bool):
        self.has_access = has_access

    def instructor_has_class(self, instructor_id, class_id):
        return self.has_access


class FakeAttendanceService:
    """Returns canned data matching AttendanceSessionResponse schema."""

    def get_session_report(self, session_id, class_id):
        return {
            "session_id": str(session_id),
            "class_id": str(class_id),
            "created_at": "2026-03-06T10:00:00Z",
            "present_students": [
                {
                    "student_id": STUB_STUDENT_ID,
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "confidence": 0.94,
                },
            ],
            "unknown_count": 2,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear FastAPI dependency overrides after each test."""
    from app.main import app

    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_instructor_gets_session_report(authenticated_client, mock_instructor_user):
    """Happy path: instructor who owns the class receives a valid report."""
    from app.main import app

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(True)
    app.dependency_overrides[get_attendance_service] = lambda: FakeAttendanceService()

    response = authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}"
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["session_id"] == str(STUB_SESSION_ID)
    assert payload["class_id"] == str(STUB_CLASS_ID)
    assert payload["created_at"] == "2026-03-06T10:00:00Z"
    assert len(payload["present_students"]) == 1
    assert payload["present_students"][0]["student_id"] == STUB_STUDENT_ID
    assert payload["present_students"][0]["first_name"] == "Jane"
    assert payload["present_students"][0]["confidence"] == 0.94
    assert payload["unknown_count"] == 2


def test_class_not_owned_returns_404(authenticated_client):
    """Instructor who does NOT own the class gets 404 (not 403)."""
    from app.main import app

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(False)
    app.dependency_overrides[get_attendance_service] = lambda: FakeAttendanceService()

    response = authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Class not found"


def test_student_forbidden(student_authenticated_client):
    """Students cannot access attendance session reports."""
    response = student_authenticated_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Instructor access required"


def test_unauthenticated_returns_401(test_client):
    """Unauthenticated requests are rejected."""
    response = test_client.get(
        f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
