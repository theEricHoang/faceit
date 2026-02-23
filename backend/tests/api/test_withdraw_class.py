import uuid

import pytest
from fastapi import status

from app.api.routes.courses import get_enrollment_service
from app.services.enrollment_service import EnrollmentServiceError


class FakeEnrollService:
    def __init__(self, behavior: str = "success"):
        self.behavior = behavior

    def withdraw_from_class(self, student_user_id, class_id):
        if self.behavior == "success":
            return {
                "class_id": str(class_id),
                "student_id": str(student_user_id),
            }
        elif self.behavior == "not_enrolled":
            raise EnrollmentServiceError("Not enrolled in this class")
        else:
            raise EnrollmentServiceError("Withdraw failed")


@pytest.fixture(autouse=True)
def clear_overrides():
    from app.main import app
    yield
    app.dependency_overrides.clear()


def test_withdraw_success(student_authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("success")
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    resp = student_authenticated_client.delete(f"/classes/{class_id}/withdraw")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["class_id"] == str(class_id)


def test_withdraw_requires_student(authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("success")
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    resp = authenticated_client.delete(f"/classes/{class_id}/withdraw")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_withdraw_not_enrolled(student_authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("not_enrolled")
    class_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    resp = student_authenticated_client.delete(f"/classes/{class_id}/withdraw")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Not enrolled" in resp.json()["detail"]
