import uuid

import pytest
from fastapi import status

from app.api.routes.courses import get_query_service, get_storage_service


class FakeQueryService:
    def __init__(self, has_access: bool):
        self.has_access = has_access

    def instructor_has_class(self, instructor_id, class_id):
        return self.has_access


class FakeStorageService:
    def generate_attendance_presigned_upload_url(
        self, class_id: str, instructor_id: str, file_extension: str = "jpg"
    ):
        return {
            "upload_url": "https://test-bucket.s3.amazonaws.com/presigned-url",
            "bucket": "test-bucket",
            "key": (
                f"attendance-photos/class-{class_id}/"
                f"instructor-{instructor_id}/20260228T120000Z-abc.jpg"
            ),
        }


@pytest.fixture(autouse=True)
def clear_overrides():
    from app.main import app
    yield
    app.dependency_overrides.clear()


def test_instructor_gets_attendance_upload_url(
    authenticated_client, mock_instructor_user
):
    from app.main import app
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(True)
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService()

    response = authenticated_client.post(f"/classes/{class_id}/attendance/upload-url")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["upload_url"] == "https://test-bucket.s3.amazonaws.com/presigned-url"
    assert payload["bucket"] == "test-bucket"
    assert f"class-{class_id}" in payload["key"]
    assert f"instructor-{mock_instructor_user.user_id}" in payload["key"]


def test_class_not_owned_returns_404(authenticated_client):
    from app.main import app
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    app.dependency_overrides[get_query_service] = lambda: FakeQueryService(False)
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService()

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
