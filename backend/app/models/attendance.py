"""Pydantic models mirroring the planned attendance DB tables.

These tables do not exist yet.
Models are defined here for documentation and type-checking purposes.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AttendanceSession(BaseModel):
    """Mirrors the planned attendance_sessions table."""

    id: UUID
    class_id: UUID
    instructor_id: UUID
    job_id: UUID
    captured_at: datetime
    created_at: datetime


class AttendanceResult(BaseModel):
    """Mirrors the planned attendance_results table.

    student_user_id is nullable: NULL means the face was detected
    but could not be matched to any enrolled student (UNKNOWN).
    """

    id: UUID
    session_id: UUID
    student_user_id: Optional[UUID]
    confidence: float
    matched_embedding_id: Optional[UUID]
    face_index: int
    created_at: datetime
