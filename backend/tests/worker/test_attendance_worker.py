"""Unit tests for AttendanceWorker."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.recognition_service import (
    FaceMatch,
    NoEnrolledStudentsError,
)
from app.utils.embedding_extractor import NoFaceDetectedError

from tests.conftest import MockTableResponse


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------

TEST_JOB_ID = "job-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "user-00000000-0000-0000-0000-000000000001"
TEST_CLASS_ID = "class-0000-0000-0000-0000-000000000001"
TEST_SESSION_ID = "sess-0000-0000-0000-0000-000000000001"
TEST_BUCKET = "test-bucket"
TEST_KEY = "attendance-photos/test/photo.jpg"
TEST_RECEIPT = "test-receipt-handle"
TEST_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/attendance-queue"

STUDENT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STUDENT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sqs_message(body: dict, receipt_handle: str = TEST_RECEIPT) -> dict:
    return {
        "Body": json.dumps(body),
        "ReceiptHandle": receipt_handle,
    }


def _make_valid_body(
    job_id: str = TEST_JOB_ID,
    user_id: str = TEST_USER_ID,
    class_id: str = TEST_CLASS_ID,
    s3_bucket: str = TEST_BUCKET,
    s3_key: str = TEST_KEY,
) -> dict:
    return {
        "job_id": job_id,
        "user_id": user_id,
        "class_id": class_id,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
    }


def _build_worker(mock_supabase, mock_recognition_service=None, embedding_mode: str = "v0"):
    """Build an AttendanceWorker with mocked dependencies."""
    with patch("app.worker.attendance_worker.get_settings") as mock_settings, \
         patch("app.worker.attendance_worker.get_sqs_client") as mock_get_sqs, \
         patch("app.worker.attendance_worker.get_s3_client") as mock_get_s3:

        settings = MagicMock()
        settings.sqs_attendance_queue_url = TEST_QUEUE_URL
        settings.s3_attendance_bucket = TEST_BUCKET
        settings.sqs_max_messages = 5
        settings.sqs_wait_time_seconds = 10
        settings.worker_max_empty_polls = 3
        settings.worker_poll_sleep_seconds = 0
        settings.worker_embedding_mode = embedding_mode
        mock_settings.return_value = settings

        mock_sqs = MagicMock()
        mock_s3 = MagicMock()
        mock_get_sqs.return_value = mock_sqs
        mock_get_s3.return_value = mock_s3

        from app.worker.attendance_worker import AttendanceWorker
        worker = AttendanceWorker(
            client=mock_supabase,
            recognition_service=mock_recognition_service,
        )
        worker.sqs_client = mock_sqs
        worker.s3_client = mock_s3

    return worker, mock_sqs, mock_s3


def _setup_supabase_happy_path(mock_supabase):
    """Configure mock supabase for successful attendance processing."""
    jobs_table = MagicMock()
    sessions_table = MagicMock()
    results_table = MagicMock()

    def table_side_effect(name):
        if name == "jobs":
            return jobs_table
        if name == "attendance_sessions":
            return sessions_table
        if name == "attendance_results":
            return results_table
        return MagicMock()

    mock_supabase.table.side_effect = table_side_effect

    # Jobs table: get status, update status
    jobs_select = MagicMock()
    jobs_table.select.return_value = jobs_select
    jobs_select.eq.return_value = jobs_select
    jobs_select.single.return_value = jobs_select
    jobs_select.execute.return_value = MockTableResponse(data={"status": "QUEUED"})

    jobs_update = MagicMock()
    jobs_table.update.return_value = jobs_update
    jobs_update.eq.return_value = jobs_update
    jobs_update.execute.return_value = MockTableResponse(data=[{"id": TEST_JOB_ID}])

    # Sessions table: get session for job
    sessions_select = MagicMock()
    sessions_table.select.return_value = sessions_select
    sessions_select.eq.return_value = sessions_select
    sessions_select.single.return_value = sessions_select
    sessions_select.execute.return_value = MockTableResponse(data={"id": TEST_SESSION_ID})

    # Results table: insert results
    results_insert = MagicMock()
    results_table.insert.return_value = results_insert
    results_insert.execute.return_value = MockTableResponse(data=[{"id": "result-1"}])

    return jobs_table, sessions_table, results_table


# ============================================================================
# Tests: Message Handling
# ============================================================================


class TestHandleMessage:
    """Tests for AttendanceWorker._handle_message()."""

    def test_happy_path_v0_with_matches(self):
        """Test successful attendance processing with recognized students."""
        mock_supabase = MagicMock()
        jobs_table, sessions_table, results_table = _setup_supabase_happy_path(mock_supabase)

        # Mock recognition service
        mock_recognition = MagicMock()
        mock_recognition.recognize_class_photo.return_value = (
            [
                FaceMatch(face_index=0, student_id=STUDENT_A_ID, confidence=0.95, quality_score=0.9),
                FaceMatch(face_index=1, student_id=STUDENT_B_ID, confidence=0.87, quality_score=0.85),
                FaceMatch(face_index=2, student_id=None, confidence=0.3, quality_score=0.8),  # UNKNOWN
            ],
            {
                "total_faces": 3,
                "present_count": 2,
                "unknown_count": 1,
                "enrolled_count": 5,
            },
        )

        worker, mock_sqs, mock_s3 = _build_worker(
            mock_supabase,
            mock_recognition_service=mock_recognition,
            embedding_mode="v0",
        )

        # S3 download returns fake image bytes
        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-class-photo"
        mock_s3.get_object.return_value = {"Body": mock_body}

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Verify S3 download
        mock_s3.get_object.assert_called_once_with(Bucket=TEST_BUCKET, Key=TEST_KEY)

        # Verify recognition was called
        mock_recognition.recognize_class_photo.assert_called_once()

        # Verify attendance_results were inserted
        results_table.insert.assert_called_once()
        inserted_rows = results_table.insert.call_args[0][0]
        assert len(inserted_rows) == 3
        assert inserted_rows[0]["student_id"] == STUDENT_A_ID
        assert inserted_rows[1]["student_id"] == STUDENT_B_ID
        assert inserted_rows[2]["student_id"] is None  # UNKNOWN

        # Verify job was marked SUCCEEDED with summary
        update_calls = jobs_table.update.call_args_list
        # First call: RUNNING, Second call: SUCCEEDED with summary
        assert len(update_calls) == 2
        final_update = update_calls[1][0][0]
        assert final_update["status"] == "SUCCEEDED"
        assert final_update["present_count"] == 2
        assert final_update["unknown_count"] == 1

        # Verify message was deleted from queue
        mock_sqs.delete_message.assert_called_once_with(
            QueueUrl=TEST_QUEUE_URL,
            ReceiptHandle=TEST_RECEIPT,
        )

    def test_all_unknown_faces(self):
        """Test attendance processing when no faces match enrolled students."""
        mock_supabase = MagicMock()
        jobs_table, sessions_table, results_table = _setup_supabase_happy_path(mock_supabase)

        mock_recognition = MagicMock()
        mock_recognition.recognize_class_photo.return_value = (
            [
                FaceMatch(face_index=0, student_id=None, confidence=0.3, quality_score=0.9),
                FaceMatch(face_index=1, student_id=None, confidence=0.2, quality_score=0.85),
            ],
            {
                "total_faces": 2,
                "present_count": 0,
                "unknown_count": 2,
                "enrolled_count": 5,
            },
        )

        worker, mock_sqs, mock_s3 = _build_worker(
            mock_supabase,
            mock_recognition_service=mock_recognition,
            embedding_mode="v0",
        )

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Job should still succeed even with no matches
        update_calls = jobs_table.update.call_args_list
        final_update = update_calls[-1][0][0]
        assert final_update["status"] == "SUCCEEDED"
        assert final_update["present_count"] == 0
        assert final_update["unknown_count"] == 2

    def test_missing_class_id_fails(self):
        """Test that missing class_id in message causes failure."""
        mock_supabase = MagicMock()
        jobs_table, _, _ = _setup_supabase_happy_path(mock_supabase)

        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v0")

        # Message missing class_id
        invalid_body = {
            "job_id": TEST_JOB_ID,
            "user_id": TEST_USER_ID,
            # "class_id" missing
            "s3_bucket": TEST_BUCKET,
            "s3_key": TEST_KEY,
        }
        message = _make_sqs_message(invalid_body)
        worker._handle_message(message)

        # Job should be marked as failed
        update_calls = jobs_table.update.call_args_list
        # Should have a FAILED update
        for call in update_calls:
            payload = call[0][0]
            if payload.get("status") == "FAILED":
                assert "error_message" in payload
                break
        else:
            pytest.fail("Expected job to be marked as FAILED")

        # Message should NOT be deleted (allow retry)
        mock_sqs.delete_message.assert_not_called()

    def test_no_faces_detected_fails(self):
        """Test handling when no faces are detected in the photo."""
        mock_supabase = MagicMock()
        jobs_table, sessions_table, results_table = _setup_supabase_happy_path(mock_supabase)

        mock_recognition = MagicMock()
        # Simulate no enrolled students error
        mock_recognition.recognize_class_photo.side_effect = NoEnrolledStudentsError(
            "No enrolled students"
        )

        worker, mock_sqs, mock_s3 = _build_worker(
            mock_supabase,
            mock_recognition_service=mock_recognition,
            embedding_mode="v0",
        )

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Job should be marked as failed
        update_calls = jobs_table.update.call_args_list
        final_call = update_calls[-1][0][0]
        assert final_call["status"] == "FAILED"
        assert "NO_ENROLLED_STUDENTS" in final_call.get("error_message", "")

    def test_already_succeeded_job_skipped(self):
        """Test that already succeeded jobs are skipped (idempotency)."""
        mock_supabase = MagicMock()
        jobs_table = MagicMock()
        mock_supabase.table.return_value = jobs_table

        # Return SUCCEEDED status
        jobs_select = MagicMock()
        jobs_table.select.return_value = jobs_select
        jobs_select.eq.return_value = jobs_select
        jobs_select.single.return_value = jobs_select
        jobs_select.execute.return_value = MockTableResponse(data={"status": "SUCCEEDED"})

        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v0")

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # S3 should NOT be called (job already done)
        mock_s3.get_object.assert_not_called()

        # Message should be deleted
        mock_sqs.delete_message.assert_called_once()

    def test_no_session_for_job_fails(self):
        """Test handling when no attendance session is linked to the job."""
        mock_supabase = MagicMock()
        jobs_table = MagicMock()
        sessions_table = MagicMock()

        def table_side_effect(name):
            if name == "jobs":
                return jobs_table
            if name == "attendance_sessions":
                return sessions_table
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        # Jobs table returns QUEUED status
        jobs_select = MagicMock()
        jobs_table.select.return_value = jobs_select
        jobs_select.eq.return_value = jobs_select
        jobs_select.single.return_value = jobs_select
        jobs_select.execute.return_value = MockTableResponse(data={"status": "QUEUED"})

        jobs_update = MagicMock()
        jobs_table.update.return_value = jobs_update
        jobs_update.eq.return_value = jobs_update
        jobs_update.execute.return_value = MockTableResponse(data=[{"id": TEST_JOB_ID}])

        # Sessions table returns None (no session found)
        sessions_select = MagicMock()
        sessions_table.select.return_value = sessions_select
        sessions_select.eq.return_value = sessions_select
        sessions_select.single.return_value = sessions_select
        sessions_select.execute.return_value = MockTableResponse(data=None)

        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v0")

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Job should be marked as failed
        update_calls = jobs_table.update.call_args_list
        final_call = update_calls[-1][0][0]
        assert final_call["status"] == "FAILED"


# ============================================================================
# Tests: SQS Message Parsing
# ============================================================================


class TestParseMessageBody:
    """Tests for message body parsing."""

    def test_parses_direct_json(self):
        """Test parsing a direct JSON message body."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase, embedding_mode="v0")

        body = json.dumps({"job_id": "123", "user_id": "456"})
        result = worker._parse_message_body(body)

        assert result["job_id"] == "123"
        assert result["user_id"] == "456"

    def test_parses_sns_wrapped_message(self):
        """Test parsing an SNS-wrapped message (double-encoded JSON)."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase, embedding_mode="v0")

        inner = {"job_id": "123", "user_id": "456"}
        body = json.dumps({"Message": json.dumps(inner)})
        result = worker._parse_message_body(body)

        assert result["job_id"] == "123"
        assert result["user_id"] == "456"

    def test_empty_body_raises_error(self):
        """Test that empty body raises ValueError."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase, embedding_mode="v0")

        with pytest.raises(ValueError, match="empty"):
            worker._parse_message_body(None)

        with pytest.raises(ValueError, match="empty"):
            worker._parse_message_body("")
