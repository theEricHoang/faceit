"""Pydantic models mirroring the attendance DB tables."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AttendanceSession(BaseModel):
    """Mirrors the attendance_sessions table."""

    id: UUID
    class_id: UUID
    instructor_id: UUID
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None


class AttendanceResult(BaseModel):
    """Mirrors the attendance_results table.

    student_id is nullable: NULL means the face was detected
    but could not be matched to any enrolled student (UNKNOWN).
    """

    id: UUID
    session_id: UUID
    student_id: Optional[UUID] = None
    confidence: Optional[float] = None
    face_index: Optional[int] = None
    created_at: Optional[datetime] = None
