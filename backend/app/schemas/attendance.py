"""Request/response schemas for attendance session reports."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PresentStudent(BaseModel):
    """A student recognized as present in an attendance session."""

    student_id: UUID
    first_name: str
    last_name: str
    confidence: Optional[float] = None


class CreateAttendanceJobResponse(BaseModel):
    """Response for attendance job creation (process endpoint)."""

    job_id: UUID
    session_id: UUID


class AttendanceSessionResponse(BaseModel):
    """Display-ready attendance session report."""

    session_id: UUID
    class_id: UUID
    created_at: Optional[datetime] = None
    present_students: list[PresentStudent]
    unknown_count: int
