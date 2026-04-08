"""Unit tests for AttendanceService."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.services.attendance_service import (
    AttendanceService,
    AttendanceServiceError,
    CreateSessionError,
    SessionNotFoundError,
)

SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
CLASS_ID = UUID("11111111-1111-1111-1111-111111111111")
STUDENT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STUDENT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockResponse:
    """Lightweight stand-in for Supabase execute() results."""

    def __init__(self, data):
        self.data = data


def _build_mock_client(session_data, results_data, profiles_data):
    """Build a MagicMock Supabase client with chainable table queries.

    Each table call is routed to the correct mock chain based on the
    table name passed to client.table().
    """
    client = MagicMock()

    def table_router(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.maybe_single.return_value = chain

        if table_name == "attendance_sessions":
            chain.execute.return_value = MockResponse(session_data)
        elif table_name == "attendance_results":
            chain.execute.return_value = MockResponse(results_data)
        elif table_name == "profiles":
            chain.execute.return_value = MockResponse(profiles_data)
        else:
            chain.execute.return_value = MockResponse(None)

        return chain

    client.table.side_effect = table_router
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetSessionReport:
    """Tests for AttendanceService.get_session_report."""

    def test_happy_path_with_recognized_and_unknown(self):
        """Returns present students with names and correct unknown count."""
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[
                {"student_id": STUDENT_A_ID, "confidence": 0.94},
                {"student_id": STUDENT_B_ID, "confidence": 0.87},
                {"student_id": None, "confidence": 0.32},
            ],
            profiles_data=[
                {"id": STUDENT_A_ID, "first_name": "Jane", "last_name": "Smith"},
                {"id": STUDENT_B_ID, "first_name": "Bob", "last_name": "Jones"},
            ],
        )

        service = AttendanceService(client=mock_client)
        report = service.get_session_report(SESSION_ID, CLASS_ID)

        assert report["session_id"] == str(SESSION_ID)
        assert report["class_id"] == str(CLASS_ID)
        assert report["created_at"] == "2026-03-06T10:00:00Z"
        assert len(report["present_students"]) == 2
        assert report["unknown_count"] == 1

        names = {s["first_name"] for s in report["present_students"]}
        assert names == {"Jane", "Bob"}

    def test_all_unknown_faces(self):
        """Session where no faces were matched returns empty present list."""
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[
                {"student_id": None, "confidence": 0.21},
                {"student_id": None, "confidence": 0.18},
            ],
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)
        report = service.get_session_report(SESSION_ID, CLASS_ID)

        assert report["present_students"] == []
        assert report["unknown_count"] == 2

    def test_duplicate_student_rows_are_collapsed(self):
        """Repeated recognized rows for one student should only appear once."""
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[
                {"student_id": STUDENT_A_ID, "confidence": 0.72},
                {"student_id": STUDENT_A_ID, "confidence": 0.94},
                {"student_id": None, "confidence": 0.19},
            ],
            profiles_data=[
                {"id": STUDENT_A_ID, "first_name": "Jane", "last_name": "Smith"},
            ],
        )

        service = AttendanceService(client=mock_client)
        report = service.get_session_report(SESSION_ID, CLASS_ID)

        assert len(report["present_students"]) == 1
        assert report["present_students"][0]["student_id"] == STUDENT_A_ID
        assert report["present_students"][0]["confidence"] == 0.94
        assert report["unknown_count"] == 1

    def test_no_results(self):
        """Session exists but has zero attendance results."""
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[],
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)
        report = service.get_session_report(SESSION_ID, CLASS_ID)

        assert report["present_students"] == []
        assert report["unknown_count"] == 0

    def test_session_not_found_raises(self):
        """Raises SessionNotFoundError when session does not exist."""
        mock_client = _build_mock_client(
            session_data=None,
            results_data=[],
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)

        with pytest.raises(SessionNotFoundError):
            service.get_session_report(SESSION_ID, CLASS_ID)

    def test_missing_profile_falls_back_to_empty_names(self):
        """If a profile is missing, names default to empty strings."""
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[
                {"student_id": STUDENT_A_ID, "confidence": 0.91},
            ],
            # No profile returned for STUDENT_A
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)
        report = service.get_session_report(SESSION_ID, CLASS_ID)

        assert len(report["present_students"]) == 1
        student = report["present_students"][0]
        assert student["student_id"] == STUDENT_A_ID
        assert student["first_name"] == ""
        assert student["last_name"] == ""

    def test_db_error_raises_attendance_service_error(self):
        """Unexpected DB errors are wrapped in AttendanceServiceError."""
        client = MagicMock()
        client.table.side_effect = Exception("connection lost")

        service = AttendanceService(client=client)

        with pytest.raises(AttendanceServiceError, match="connection lost"):
            service.get_session_report(SESSION_ID, CLASS_ID)


class TestBuildSessionReportPdf:
    """Tests for AttendanceService.build_session_report_pdf."""

    def test_builds_a_pdf_document(self):
        service = AttendanceService(client=MagicMock())
        pdf_bytes = service.build_session_report_pdf(
            {
                "session_id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "created_at": "2026-03-06T10:00:00Z",
                "present_students": [
                    {
                        "student_id": STUDENT_A_ID,
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "confidence": 0.94,
                    },
                ],
                "unknown_count": 1,
            },
            {
                "course_code": "CS101",
                "course_name": "Intro to Computing",
                "section": "A",
                "schedule": "Mon/Wed 10:00 AM",
                "room": "Room 12",
                "instructor_name": "Dr. Ada Lovelace",
            },
        )

        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000


# ---------------------------------------------------------------------------
# CreateSession Tests
# ---------------------------------------------------------------------------

JOB_ID = UUID("33333333-3333-3333-3333-333333333333")
INSTRUCTOR_ID = UUID("44444444-4444-4444-4444-444444444444")


class TestCreateSession:
    """Tests for AttendanceService.create_session."""

    def test_happy_path_creates_session_row(self):
        """Inserts row with correct class_id, instructor_id, job_id. Returns row with id."""
        mock_client = MagicMock()
        created_row = {
            "id": "55555555-5555-5555-5555-555555555555",
            "class_id": str(CLASS_ID),
            "instructor_id": str(INSTRUCTOR_ID),
            "job_id": str(JOB_ID),
        }
        mock_client.table.return_value.insert.return_value.execute.return_value = MockResponse(
            data=[created_row]
        )

        service = AttendanceService(client=mock_client)
        result = service.create_session(
            class_id=CLASS_ID, instructor_id=INSTRUCTOR_ID, job_id=JOB_ID
        )

        assert result["id"] == "55555555-5555-5555-5555-555555555555"
        assert result["class_id"] == str(CLASS_ID)
        assert result["instructor_id"] == str(INSTRUCTOR_ID)
        assert result["job_id"] == str(JOB_ID)

        # Verify insert was called on attendance_sessions table
        mock_client.table.assert_called_with("attendance_sessions")
        insert_args = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_args["id"] is None
        assert insert_args["class_id"] == str(CLASS_ID)
        assert insert_args["instructor_id"] == str(INSTRUCTOR_ID)
        assert insert_args["job_id"] == str(JOB_ID)

    def test_happy_path_creates_session_row_with_explicit_id(self):
        """Allows callers to pin the batch session id up front."""
        mock_client = MagicMock()
        created_row = {
            "id": str(SESSION_ID),
            "class_id": str(CLASS_ID),
            "instructor_id": str(INSTRUCTOR_ID),
            "job_id": str(JOB_ID),
        }
        mock_client.table.return_value.insert.return_value.execute.return_value = MockResponse(
            data=[created_row]
        )

        service = AttendanceService(client=mock_client)
        result = service.create_session(
            class_id=CLASS_ID,
            instructor_id=INSTRUCTOR_ID,
            job_id=JOB_ID,
            session_id=SESSION_ID,
        )

        assert result["id"] == str(SESSION_ID)
        insert_args = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_args["id"] == str(SESSION_ID)

    def test_db_error_raises_create_session_error(self):
        """DB exception is wrapped in CreateSessionError."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "DB connection error"
        )

        service = AttendanceService(client=mock_client)
        with pytest.raises(CreateSessionError, match="Failed to create attendance session"):
            service.create_session(
                class_id=CLASS_ID, instructor_id=INSTRUCTOR_ID, job_id=JOB_ID
            )


# ---------------------------------------------------------------------------
# GetSessionIdForJob Tests
# ---------------------------------------------------------------------------


class TestGetSessionIdForJob:
    """Tests for AttendanceService.get_session_id_for_job."""

    def test_happy_path_returns_session_id(self):
        """Returns the session ID when a matching row exists."""
        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.single.return_value = chain
        chain.execute.return_value = MockResponse(data={"id": str(SESSION_ID)})
        mock_client.table.return_value = chain

        service = AttendanceService(client=mock_client)
        result = service.get_session_id_for_job(JOB_ID)

        assert result == str(SESSION_ID)
        mock_client.table.assert_called_with("attendance_sessions")
        chain.select.assert_called_once_with("id")
        chain.eq.assert_called_once_with("job_id", str(JOB_ID))

    def test_not_found_raises_session_not_found_error(self):
        """Raises SessionNotFoundError when .single() throws (no row)."""
        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.single.return_value = chain
        chain.execute.side_effect = Exception("Row not found")
        mock_client.table.return_value = chain

        service = AttendanceService(client=mock_client)
        with pytest.raises(SessionNotFoundError, match="No attendance session found"):
            service.get_session_id_for_job(JOB_ID)


class TestGetSession:
    """Tests for AttendanceService.get_session."""

    def test_happy_path_returns_session_row(self):
        mock_client = _build_mock_client(
            session_data={
                "id": str(SESSION_ID),
                "class_id": str(CLASS_ID),
                "instructor_id": str(INSTRUCTOR_ID),
                "job_id": str(JOB_ID),
                "created_at": "2026-03-06T10:00:00Z",
            },
            results_data=[],
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)
        session = service.get_session(SESSION_ID, CLASS_ID)

        assert session["id"] == str(SESSION_ID)
        assert session["job_id"] == str(JOB_ID)

    def test_missing_session_raises_not_found(self):
        mock_client = _build_mock_client(
            session_data=None,
            results_data=[],
            profiles_data=[],
        )

        service = AttendanceService(client=mock_client)
        with pytest.raises(SessionNotFoundError, match="not found"):
            service.get_session(SESSION_ID, CLASS_ID)
