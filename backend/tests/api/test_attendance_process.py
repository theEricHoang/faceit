"""Tests for POST /classes/{class_id}/attendance/process/{job_id}
and GET /classes/{class_id}/attendance/jobs/{job_id}/status."""

import uuid

import pytest
from fastapi import status

from app.api.deps import get_attendance_service, get_job_service, get_query_service
from app.services.job_service import (
    CreateJobError,
    JobNotFoundError,
    JobNotPendingError,
    JobOwnershipError,
)
from app.services.attendance_service import SessionNotFoundError
from app.schemas.attendance import CreateAttendanceJobResponse


# ---------------------------------------------------------------------------
# Stub constants
# ---------------------------------------------------------------------------

STUB_CLASS_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
STUB_JOB_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
STUB_SESSION_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


# ---------------------------------------------------------------------------
# Fake service doubles
# ---------------------------------------------------------------------------


class FakeQueryService:
    """Configurable stub for ClassQueryService."""

    def __init__(self, has_access: bool):
        self.has_access = has_access

    def instructor_has_class(self, instructor_id, class_id):
        return self.has_access


class FakeAttendanceService:
    """Stub for AttendanceService — returns a canned session_id or raises."""

    def __init__(self, session_id=None, error=None):
        self._session_id = session_id or str(STUB_SESSION_ID)
        self._error = error

    def get_session_id_for_job(self, job_id):
        if self._error:
            raise self._error
        return self._session_id

    def get_session(self, session_id, class_id):
        if self._error:
            raise self._error
        return {
            "id": str(session_id),
            "class_id": str(class_id),
            "job_id": str(STUB_JOB_ID),
        }


class FakeJobService:
    """Stub that returns canned responses or raises configured errors."""

    def __init__(self, enqueue_error=None, status_error=None, status_data=None):
        self._enqueue_error = enqueue_error
        self._status_error = status_error
        self._status_data = status_data

    def enqueue_attendance_job(self, job_id, user_id, class_id, session_id):
        if self._enqueue_error:
            raise self._enqueue_error
        return CreateAttendanceJobResponse(
            job_id=STUB_JOB_ID, session_id=STUB_SESSION_ID
        )

    async def get_job_status(self, job_id, owner_user_id):
        if self._status_error:
            raise self._status_error
        return self._status_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear FastAPI dependency overrides after each test."""
    from app.main import app

    yield
    app.dependency_overrides.clear()


def _apply_overrides(has_access=True, job_service=None, attendance_service=None):
    from app.main import app

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(has_access)
    if job_service is not None:
        app.dependency_overrides[get_job_service] = lambda: job_service
    if attendance_service is not None:
        app.dependency_overrides[get_attendance_service] = lambda: attendance_service
    else:
        # Default: provide a working FakeAttendanceService
        app.dependency_overrides[get_attendance_service] = lambda: FakeAttendanceService()


# ===========================================================================
# Tests: POST /{class_id}/attendance/process/{job_id}
# ===========================================================================


class TestAttendanceProcess:
    """Tests for the attendance process endpoint."""

    def test_happy_path_enqueues_and_returns_ids(
        self, authenticated_client, mock_instructor_user
    ):
        _apply_overrides(has_access=True, job_service=FakeJobService())

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["job_id"] == str(STUB_JOB_ID)
        assert payload["session_id"] == str(STUB_SESSION_ID)

    def test_session_process_happy_path_returns_ids(
        self, authenticated_client, mock_instructor_user
    ):
        _apply_overrides(has_access=True, job_service=FakeJobService())

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/sessions/{STUB_SESSION_ID}/process"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["job_id"] == str(STUB_JOB_ID)
        assert payload["session_id"] == str(STUB_SESSION_ID)

    def test_class_not_owned_returns_404(self, authenticated_client):
        _apply_overrides(has_access=False, job_service=FakeJobService())

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Class not found"

    def test_student_forbidden_returns_403(self, student_authenticated_client):
        response = student_authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Instructor access required"

    def test_unauthenticated_returns_401(self, test_client):
        response = test_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_job_not_found_returns_404(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(
                enqueue_error=JobNotFoundError(f"Job {STUB_JOB_ID} not found")
            ),
        )

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_job_not_pending_returns_400(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(
                enqueue_error=JobNotPendingError(
                    "Job is not in PENDING status (current: RUNNING)"
                )
            ),
        )

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_job_ownership_error_returns_400(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(
                enqueue_error=JobOwnershipError(
                    "Job does not belong to the authenticated user"
                )
            ),
        )

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generic_create_job_error_returns_500(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(
                enqueue_error=CreateJobError("Failed to enqueue job: SQS unavailable")
            ),
        )

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_session_not_found_returns_404(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(),
            attendance_service=FakeAttendanceService(
                error=SessionNotFoundError("No attendance session found for this job")
            ),
        )

        response = authenticated_client.post(
            f"/classes/{STUB_CLASS_ID}/attendance/process/{STUB_JOB_ID}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "attendance session" in response.json()["detail"].lower()


# ===========================================================================
# Tests: GET /{class_id}/attendance/jobs/{job_id}/status
# ===========================================================================


class TestAttendanceJobStatus:
    """Tests for the attendance job status endpoint."""

    def test_happy_path_returns_status(self, authenticated_client, mock_instructor_user):
        from app.schemas.job import JobStatusResponse

        fake_status = JobStatusResponse(
            job_id=STUB_JOB_ID,
            status="PENDING",
            kind="ATTENDANCE",
            error_message=None,
            updated_at="2026-03-10T12:00:00Z",
        )
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(status_data=fake_status),
        )

        response = authenticated_client.get(
            f"/classes/{STUB_CLASS_ID}/attendance/jobs/{STUB_JOB_ID}/status"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["job_id"] == str(STUB_JOB_ID)
        assert payload["status"] == "PENDING"
        assert payload["kind"] == "ATTENDANCE"

    def test_class_not_owned_returns_404(self, authenticated_client):
        _apply_overrides(has_access=False, job_service=FakeJobService())

        response = authenticated_client.get(
            f"/classes/{STUB_CLASS_ID}/attendance/jobs/{STUB_JOB_ID}/status"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Class not found"

    def test_job_not_found_returns_404(self, authenticated_client):
        _apply_overrides(
            has_access=True,
            job_service=FakeJobService(
                status_error=JobNotFoundError(f"Job {STUB_JOB_ID} not found")
            ),
        )

        response = authenticated_client.get(
            f"/classes/{STUB_CLASS_ID}/attendance/jobs/{STUB_JOB_ID}/status"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Job not found"

    def test_student_forbidden_returns_403(self, student_authenticated_client):
        response = student_authenticated_client.get(
            f"/classes/{STUB_CLASS_ID}/attendance/jobs/{STUB_JOB_ID}/status"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_returns_401(self, test_client):
        response = test_client.get(
            f"/classes/{STUB_CLASS_ID}/attendance/jobs/{STUB_JOB_ID}/status"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
