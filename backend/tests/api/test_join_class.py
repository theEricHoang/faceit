import uuid

import pytest
from fastapi import status

from app.api.routes.courses import get_enrollment_service
from app.services.enrollment_service import EnrollmentServiceError


class FakeEnrollService:
    def __init__(self, behavior: str = "success"):
        self.behavior = behavior

    def join_by_section(self, student_user_id, section: str):
        if self.behavior == "success":
            return {
                "class_id": "11111111-1111-1111-1111-111111111111",
                "student_id": str(student_user_id),
                "course_name": "Intro CS",
                "section": "A",
            }
        elif self.behavior == "not_found":
            raise EnrollmentServiceError("Class not found for given section")
        else:
            raise EnrollmentServiceError("Enrollment failed")


@pytest.fixture(autouse=True)
def clear_overrides():
    # Ensure overrides cleared after each test
    from app.main import app
    yield
    app.dependency_overrides.clear()


def test_join_class_success(student_authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("success")
    resp = student_authenticated_client.post("/classes/join", json={"section": "A"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["class_id"] == "11111111-1111-1111-1111-111111111111"
    assert data["course_name"] == "Intro CS"
    assert data["section"] == "A"


def test_join_class_requires_student(authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("success")
    resp = authenticated_client.post("/classes/join", json={"section": "A"})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_join_class_not_found(student_authenticated_client):
    from app.main import app
    app.dependency_overrides[get_enrollment_service] = lambda: FakeEnrollService("not_found")
    resp = student_authenticated_client.post("/classes/join", json={"section": "Z"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Class not found" in resp.json()["detail"]
