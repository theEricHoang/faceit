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
            # honor ilike filter on section
            section = None
            for kind, col, val in self._filters:
                if kind == "ilike" and col == "section":
                    section = val
            rows = [
                {
                    "id": "cls-uuid",
                    "course_code": "CS101",
                    "course_name": "Intro CS",
                    "section": "A",
                }
            ] if (section is None or section.lower() == "a") else []
            if self._limit:
                rows = rows[: self._limit]
            return FakeResponse(rows)
        elif self.name == "students":
            # find by eq id
            has_id = any(kind == "eq" and col == "id" for kind, col, _ in self._filters)
            return FakeResponse({"id": "12345678-1234-1234-1234-123456789012"} if has_id else None)
        elif self.name == "student_classes":
            # simulate existing based on stored inserts and filters
            stored_rows = self.store.get("student_classes", [])
            class_id = None
            student_id = None
            for kind, col, val in self._filters:
                if kind == "eq" and col == "class_id":
                    class_id = val
                if kind == "eq" and col == "student_id":
                    student_id = val
            rows = [
                r for r in stored_rows
                if (class_id is None or r.get("class_id") == class_id)
                and (student_id is None or r.get("student_id") == student_id)
            ]
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
    res = svc.join_by_section(UUID("12345678-1234-1234-1234-123456789012"), "A")
    assert res["class_id"] == "cls-uuid"
    assert res["student_id"] == "12345678-1234-1234-1234-123456789012"
    assert res["course_name"] == "Intro CS"
    assert res["section"] == "A"


def test_join_existing_enrollment_raises():
    client = FakeClient()
    svc = EnrollmentService(client=client)
    # First call: create enrollment
    _ = svc.join_by_section(UUID("12345678-1234-1234-1234-123456789012"), "A")
    # Second call: should raise already joined
    with pytest.raises(EnrollmentServiceError) as e:
        svc.join_by_section(UUID("12345678-1234-1234-1234-123456789012"), "A")
    assert "already joined" in str(e.value).lower()


def test_join_class_not_found_raises():
    svc = EnrollmentService(client=FakeClient())
    with pytest.raises(EnrollmentServiceError) as e:
        svc.join_by_section(UUID("12345678-1234-1234-1234-123456789012"), "Z")
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
        svc.join_by_section(UUID("12345678-1234-1234-1234-123456789012"), "A")
    assert "Student record not found" in str(e.value)
