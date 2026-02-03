import pytest
from uuid import uuid4
from app.services.classes.class_query_service import ClassService
from app.services.classes.class_read_repository import ClassReadRepository

class DummyRepo(ClassReadRepository):
    def get_classes_by_instructor(self, instructor_id):
        return [
            {
                "id": str(uuid4()),
                "course_code": "CSC4352",
                "course_name": "Capstone II",
                "section": "19884",
                "term": "Spring 2026",
                "schedule": "M-W 9:00AM-10:00AM",
                "room": "Langdale Hall 400",
            }
        ]
    def get_classes_by_student(self, student_id):
        return [
            {
                "id": str(uuid4()),
                "course_code": "MATH1738",
                "course_name": "Calculus I",
                "section": "10001",
                "term": "Fall 2025",
                "schedule": "T-Th 10:00AM-11:15AM",
                "room": "Petit Science Center 200",
            }
        ]

def test_get_classes_for_instructor():
    service = ClassService(read_repo=DummyRepo())
    user_id = uuid4()
    result = service.get_classes_for_user(user_id, "instructor")
    assert result[0]["course_code"] == "CSC4352"

def test_get_classes_for_student():
    service = ClassService(read_repo=DummyRepo())
    user_id = uuid4()
    result = service.get_classes_for_user(user_id, "student")
    assert result[0]["course_code"] == "MATH1738"
