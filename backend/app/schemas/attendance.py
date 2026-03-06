"""Request/response schemas for attendance session reports."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PresentStudent(BaseModel):
    """A student recognized as present in an attendance session."""

    student_user_id: UUID
    first_name: str
    last_name: str
    confidence: float


class AttendanceSessionResponse(BaseModel):
    """Display-ready attendance session report."""

    session_id: UUID
    class_id: UUID
    captured_at: datetime
    present_students: list[PresentStudent]
    unknown_count: int
