from uuid import UUID
from typing import Any

import pytest

from app.services.enrollment_service import EnrollmentService, EnrollmentServiceError


class FakeResponse:
    def __init__(self, data: Any):
        self.data = data


class TableChain:
    def __init__(self, name: str, store: dict):
        self.name = name
        self.store = store
        self._select_cols = None
        self._filters = []
        self._single = False
        self._limit = None

    # Query building methods
    def select(self, cols: str):
        self._select_cols = cols
        return self

    def ilike(self, col: str, value: str):
        self._filters.append(("ilike", col, value))
        return self

    def eq(self, col: str, value: str):
        self._filters.append(("eq", col, value))
        return self

    def single(self):
        self._single = True
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    # Write
    def insert(self, row: dict):
        # Simulate insert by appending to store
        self.store.setdefault(self.name, [])
        self.store[self.name].append(row | {"id": "enroll-id"})
        return self

    # Execute
    def execute(self):
        if self.name == "classes":
            # honor ilike filter on course_code
            course_code = None
            for kind, col, val in self._filters:
                if kind == "ilike" and col == "course_code":
                    course_code = val
            rows = [
                {
                    "id": "cls-uuid",
                    "course_code": "CS101",
                    "course_name": "Intro CS",
                    "section": "A",
                }
            ] if (course_code is None or course_code.lower() == "cs101") else []
            if self._limit:
                rows = rows[: self._limit]
            return FakeResponse(rows)
        elif self.name == "students":
            # find by eq id
            has_id = any(kind == "eq" and col == "id" for kind, col, _ in self._filters)
            return FakeResponse({"id": "12345678-1234-1234-1234-123456789012"} if has_id else None)
        elif self.name == "student_classes":
            # existing enrollment when both eq filters match
            class_id = None
            student_id = None
            for kind, col, val in self._filters:
                if kind == "eq" and col == "class_id":
                    class_id = val
                if kind == "eq" and col == "student_id":
                    student_id = val
            # Simulate existing if class_id == cls-uuid
            if class_id == "cls-uuid" and student_id == "12345678-1234-1234-1234-123456789012":
                rows = [{"id": "enroll-id", "class_id": class_id, "student_id": student_id}]
            else:
                rows = []
            if self._limit:
                rows = rows[: self._limit]
            return FakeResponse(rows)
        else:
            return FakeResponse(None)


class FakeClient:
    def __init__(self):
        self.store = {}

    def table(self, name: str):
        return TableChain(name, self.store)


def test_join_success_returns_details():
    svc = EnrollmentService(client=FakeClient())
    res = svc.join_by_course_code(UUID("12345678-1234-1234-1234-123456789012"), "cs101")
    assert res["class_id"] == "cls-uuid"
    assert res["student_id"] == "12345678-1234-1234-1234-123456789012"
    assert res["course_name"] == "Intro CS"
    assert res["section"] == "A"


def test_join_existing_enrollment_still_returns_details(monkeypatch):
    client = FakeClient()
    svc = EnrollmentService(client=client)
    # First call: create enrollment
    _ = svc.join_by_course_code(UUID("12345678-1234-1234-1234-123456789012"), "cs101")
    # Simulate existing on second call via FakeClient logic
    res = svc.join_by_course_code(UUID("12345678-1234-1234-1234-123456789012"), "cs101")
    assert res["class_id"] == "cls-uuid"
    assert res["course_name"] == "Intro CS"
    assert res["section"] == "A"


def test_join_class_not_found_raises():
    svc = EnrollmentService(client=FakeClient())
    with pytest.raises(EnrollmentServiceError) as e:
        svc.join_by_course_code(UUID("12345678-1234-1234-1234-123456789012"), "unknown")
    assert "Class not found" in str(e.value)


class FakeClientNoStudent(FakeClient):
    def table(self, name: str):
        chain = super().table(name)
        if name == "students":
            # Override execute to return None
            def exec_none():
                return FakeResponse(None)
            chain.execute = exec_none  # type: ignore
        return chain


def test_join_student_missing_raises():
    svc = EnrollmentService(client=FakeClientNoStudent())
    with pytest.raises(EnrollmentServiceError) as e:
        svc.join_by_course_code(UUID("12345678-1234-1234-1234-123456789012"), "cs101")
    assert "Student record not found" in str(e.value)
