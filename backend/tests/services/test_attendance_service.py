"""Unit tests for AttendanceService.get_session_report."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.services.attendance_service import (
    AttendanceService,
    AttendanceServiceError,
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
