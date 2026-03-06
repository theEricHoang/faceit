"""Service for fetching attendance session reports.

Currently returns hardcoded stub data — the attendance_sessions and
attendance_results tables do not exist yet.
"""

import logging
from uuid import UUID

from supabase import Client

from app.db.supabase import get_supabase_client

logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AttendanceServiceError(Exception):
    """Base exception for attendance service errors."""

    pass


class SessionNotFoundError(AttendanceServiceError):
    """Raised when the requested session does not exist."""

    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AttendanceService:
    """Reads attendance session data from Supabase."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def get_session_report(self, session_id: UUID, class_id: UUID) -> dict:
        """Return a display-ready attendance report for a single session.

        TODO: Replace stub with real Supabase queries once the
        attendance_sessions and attendance_results tables exist.

        Real implementation will:
            1. Query attendance_sessions filtered by session_id AND class_id
               (ensures the session belongs to the requested class).
            2. Query attendance_results joined with profiles to get student
               names for recognized faces (student_user_id IS NOT NULL).
            3. Count unknown faces (student_user_id IS NULL).
            4. Raise SessionNotFoundError if no matching session row.
        """
        # --- Stub data (remove when real tables are available) ---
        return {
            "session_id": str(session_id),
            "class_id": str(class_id),
            "captured_at": "2026-03-06T10:00:00Z",
            "present_students": [
                {
                    "student_user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "confidence": 0.94,
                },
                {
                    "student_user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    "first_name": "Bob",
                    "last_name": "Jones",
                    "confidence": 0.87,
                },
            ],
            "unknown_count": 2,
        }
