"""Service for fetching attendance session reports."""

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


class CreateSessionError(AttendanceServiceError):
    """Raised when a new attendance session cannot be created."""

    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AttendanceService:
    """Reads attendance session data from Supabase and creates new sessions."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create_session(self, class_id: UUID, instructor_id: UUID, job_id: UUID) -> dict:
        """Create an attendance session row linked to a job.

        Args:
            class_id: The class for which attendance is being taken.
            instructor_id: The instructor running the session.
            job_id: The associated processing job ID.

        Returns:
            The created row dict (including ``id`` as the session_id).

        Raises:
            CreateSessionError: If the DB insert fails.
        """
        try:
            result = (
                self.client
                .table("attendance_sessions")
                .insert(
                    {
                        "class_id": str(class_id),
                        "instructor_id": str(instructor_id),
                        "job_id": str(job_id),
                    }
                )
                .execute()
            )
            if not result.data:
                raise CreateSessionError("Failed to create attendance session")
            return result.data[0]
        except CreateSessionError:
            raise
        except Exception as e:
            logger.exception("Failed to create attendance session")
            raise CreateSessionError(
                f"Failed to create attendance session: {e}"
            ) from e

    def get_session_id_for_job(self, job_id: UUID) -> str:
        """Look up the attendance session ID linked to a job.

        Args:
            job_id: The job ID to look up.

        Returns:
            The session ID as a string.

        Raises:
            SessionNotFoundError: If no session is found for the job.
        """
        try:
            result = (
                self.client
                .table("attendance_sessions")
                .select("id")
                .eq("job_id", str(job_id))
                .single()
                .execute()
            )
        except Exception as e:
            raise SessionNotFoundError(
                f"No attendance session found for job {job_id}"
            ) from e

        if not result.data:
            raise SessionNotFoundError(
                f"No attendance session found for job {job_id}"
            )

        return result.data["id"]

    def get_session_report(self, session_id: UUID, class_id: UUID) -> dict:
        """Return a display-ready attendance report for a single session.

        Steps:
            1. Fetch the attendance_session row by session_id + class_id.
            2. Fetch all attendance_results for that session.
            3. For recognized results (student_id IS NOT NULL), look up
               student names from the profiles table.
            4. Count unknown results (student_id IS NULL).

        Raises:
            SessionNotFoundError: If no session matches the given IDs.
            AttendanceServiceError: On unexpected DB errors.
        """
        try:
            # 1. Fetch session — must belong to the requested class
            session_result = (
                self.client
                .table("attendance_sessions")
                .select("id, class_id, created_at")
                .eq("id", str(session_id))
                .eq("class_id", str(class_id))
                .maybe_single()
                .execute()
            )
            session = session_result.data
            if not session:
                raise SessionNotFoundError(
                    f"Session {session_id} not found in class {class_id}"
                )

            # 2. Fetch all results for this session
            results_response = (
                self.client
                .table("attendance_results")
                .select("student_id, confidence")
                .eq("session_id", str(session_id))
                .execute()
            )
            results = results_response.data or []

            # 3. Separate recognized vs unknown
            recognized = [r for r in results if r.get("student_id") is not None]
            unknown_count = len(results) - len(recognized)

            # 4. Batch-fetch profile names for recognized students
            present_students = []
            if recognized:
                student_ids = list({r["student_id"] for r in recognized})
                profiles_response = (
                    self.client
                    .table("profiles")
                    .select("id, first_name, last_name")
                    .in_("id", student_ids)
                    .execute()
                )
                profiles_map = {
                    p["id"]: p for p in (profiles_response.data or [])
                }

                for r in recognized:
                    sid = r["student_id"]
                    profile = profiles_map.get(sid, {})
                    present_students.append({
                        "student_id": sid,
                        "first_name": profile.get("first_name", ""),
                        "last_name": profile.get("last_name", ""),
                        "confidence": r.get("confidence"),
                    })

            return {
                "session_id": str(session["id"]),
                "class_id": str(session["class_id"]),
                "created_at": session.get("created_at"),
                "present_students": present_students,
                "unknown_count": unknown_count,
            }

        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.exception("Failed to fetch attendance session report")
            raise AttendanceServiceError(
                f"Failed to fetch session report: {e}"
            ) from e
