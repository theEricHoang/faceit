import uuid

import pytest
from fastapi import status

from app.api.deps import (
    get_query_service,
    get_storage_service,
    get_job_service,
    get_attendance_service,
)


class FakeQueryService:
    def __init__(self, has_access: bool):
        self.has_access = has_access

    def instructor_has_class(self, instructor_id, class_id):
        return self.has_access


class FakeStorageService:
    def generate_attendance_presigned_upload_url(
        self,
        class_id: str,
        instructor_id: str,
        session_id: str,
        file_extension: str = "jpg"
    ):
        return {
            "upload_url": "https://test-bucket.s3.amazonaws.com/presigned-url",
            "bucket": "test-bucket",
            "key": (
                f"attendance-photos/class-{class_id}/"
                f"instructor-{instructor_id}/session-{session_id}/20260228T120000Z-abc.jpg"
            ),
            "key_prefix": (
                f"attendance-photos/class-{class_id}/"
                f"instructor-{instructor_id}/session-{session_id}/"
            ),
        }


class FakeJobService:
    """Fake that records create_pending_attendance_job calls."""

    def create_pending_attendance_job(self, job_id, user_id, bucket, key):
        return {
            "id": job_id,
            "kind": "ATTENDANCE",
            "status": "PENDING",
            "owner_user_id": user_id,
            "s3_bucket": bucket,
            "s3_key": key,
        }

    def rollback_job(self, job_id):
        """No-op rollback for tests."""
        pass


FAKE_SESSION_ID = "99999999-9999-9999-9999-999999999999"


class FakeAttendanceService:
    """Fake that returns canned session rows for batch attendance flows."""

    def create_session(self, class_id, instructor_id, job_id, session_id=None):
        return {
            "id": str(session_id or FAKE_SESSION_ID),
            "class_id": str(class_id),
            "instructor_id": str(instructor_id),
            "job_id": str(job_id),
        }

    def get_session(self, session_id, class_id):
        return {
            "id": str(session_id),
            "class_id": str(class_id),
            "instructor_id": "instructor-id",
            "job_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        }


@pytest.fixture(autouse=True)
def clear_overrides():
    from app.main import app
    yield
    app.dependency_overrides.clear()


def _apply_overrides(has_access=True):
    """Apply all dependency overrides for the upload-url endpoint."""
    from app.main import app

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(has_access)
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService()
    app.dependency_overrides[get_job_service] = lambda: FakeJobService()
    app.dependency_overrides[get_attendance_service] = lambda: FakeAttendanceService()


def test_instructor_gets_attendance_upload_url(
    authenticated_client, mock_instructor_user
):
    _apply_overrides(has_access=True)

    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    response = authenticated_client.post(f"/classes/{class_id}/attendance/upload-url")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["upload_url"] == "https://test-bucket.s3.amazonaws.com/presigned-url"
    assert payload["bucket"] == "test-bucket"
    assert f"class-{class_id}" in payload["key"]
    assert f"instructor-{mock_instructor_user.user_id}" in payload["key"]
    assert f"session-{payload['session_id']}" in payload["key"]
    # New fields from job + session creation
    assert payload["job_id"] is not None
    assert payload["session_id"] is not None


def test_existing_session_reuses_session_and_job(authenticated_client):
    _apply_overrides(has_access=True)

    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    response = authenticated_client.post(
        f"/classes/{class_id}/attendance/upload-url?session_id={FAKE_SESSION_ID}"
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["session_id"] == FAKE_SESSION_ID
    assert payload["job_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert f"session-{FAKE_SESSION_ID}" in payload["key"]


def test_class_not_owned_returns_404(authenticated_client):
    _apply_overrides(has_access=False)

    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    response = authenticated_client.post(f"/classes/{class_id}/attendance/upload-url")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Class not found"


def test_student_forbidden(student_authenticated_client):
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    response = student_authenticated_client.post(f"/classes/{class_id}/attendance/upload-url")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Instructor access required"


def test_unauthenticated_returns_401(test_client):
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    response = test_client.post(f"/classes/{class_id}/attendance/upload-url")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
