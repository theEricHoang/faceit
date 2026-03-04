"""Unit tests for EnrollmentWorker."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.utils.embedding_extractor import (
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)

from tests.conftest import MockTableResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_JOB_ID = "job-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "user-00000000-0000-0000-0000-000000000001"
TEST_BUCKET = "test-bucket"
TEST_KEY = "enrollment-photos/test/photo.jpg"
TEST_RECEIPT = "test-receipt-handle"
TEST_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"


def _make_sqs_message(body: dict, receipt_handle: str = TEST_RECEIPT) -> dict:
    return {
        "Body": json.dumps(body),
        "ReceiptHandle": receipt_handle,
    }


def _make_valid_body(
    job_id: str = TEST_JOB_ID,
    user_id: str = TEST_USER_ID,
    s3_bucket: str = TEST_BUCKET,
    s3_key: str = TEST_KEY,
) -> dict:
    return {
        "job_id": job_id,
        "user_id": user_id,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
    }


def _build_worker(mock_supabase, embedding_mode: str = "v0"):
    """Build an EnrollmentWorker with mocked dependencies."""
    with patch("app.worker.enrollment_worker.get_settings") as mock_settings, \
         patch("app.worker.enrollment_worker.get_sqs_client") as mock_get_sqs, \
         patch("app.worker.enrollment_worker.get_s3_client") as mock_get_s3:

        settings = MagicMock()
        settings.sqs_enrollment_queue_url = TEST_QUEUE_URL
        settings.s3_enrollment_bucket = TEST_BUCKET
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

        from app.worker.enrollment_worker import EnrollmentWorker
        worker = EnrollmentWorker(client=mock_supabase)
        worker.sqs_client = mock_sqs
        worker.s3_client = mock_s3

    return worker, mock_sqs, mock_s3


def _setup_supabase_for_happy_path(mock_supabase):
    """Configure mock supabase for a successful job processing flow."""
    jobs_table = MagicMock()
    embeddings_table = MagicMock()

    def table_side_effect(name):
        if name == "jobs":
            return jobs_table
        if name == "face_embeddings":
            return embeddings_table
        return MagicMock()

    mock_supabase.table.side_effect = table_side_effect

    # _get_job_status: select -> eq -> single -> execute
    select_chain = MagicMock()
    jobs_table.select.return_value = select_chain
    select_chain.eq.return_value = select_chain
    select_chain.single.return_value = select_chain
    select_chain.execute.return_value = MockTableResponse(data={"status": "PENDING"})

    # _update_job_status: update -> eq -> execute
    update_chain = MagicMock()
    jobs_table.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MockTableResponse(data=[{"id": TEST_JOB_ID}])

    # _insert_embedding: insert -> execute
    insert_chain = MagicMock()
    embeddings_table.insert.return_value = insert_chain
    insert_chain.execute.return_value = MockTableResponse(data=[{"id": "emb-1"}])

    return jobs_table, embeddings_table


# ============================================================================
# _handle_message Tests
# ============================================================================


class TestHandleMessage:
    """Tests for EnrollmentWorker._handle_message()."""

    def test_happy_path_v0(self):
        """Test successful v0 message processing: download, stub embed, insert, succeed."""
        mock_supabase = MagicMock()
        jobs_table, embeddings_table = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v0")

        # S3 download returns fake image bytes
        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Verify S3 download was called with correct bucket/key
        mock_s3.get_object.assert_called_once_with(Bucket=TEST_BUCKET, Key=TEST_KEY)

        # Verify embedding was inserted
        embeddings_table.insert.assert_called_once()
        insert_payload = embeddings_table.insert.call_args[0][0]
        assert insert_payload["user_id"] == TEST_USER_ID
        assert insert_payload["model"] == "worker-v0"
        assert isinstance(insert_payload["embedding"], list)
        assert len(insert_payload["embedding"]) == 512

        # Verify job was marked as SUCCEEDED (second update call)
        update_calls = jobs_table.update.call_args_list
        assert len(update_calls) == 2
        assert update_calls[0][0][0]["status"] == "RUNNING"
        assert update_calls[1][0][0]["status"] == "SUCCEEDED"

        # Verify SQS message was deleted
        mock_sqs.delete_message.assert_called_once_with(
            QueueUrl=TEST_QUEUE_URL,
            ReceiptHandle=TEST_RECEIPT,
        )

    @patch("app.worker.enrollment_worker.EmbeddingExtractor")
    def test_happy_path_v1(self, mock_extractor_cls):
        """Test successful v1 message processing with InsightFace."""
        mock_supabase = MagicMock()
        jobs_table, embeddings_table = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v1")

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        mock_instance = MagicMock()
        mock_extractor_cls.get_instance.return_value = mock_instance
        mock_instance.extract_embedding.return_value = ([0.1] * 512, 0.98)

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        insert_payload = embeddings_table.insert.call_args[0][0]
        assert insert_payload["model"] == "insightface-worker-v1"
        assert insert_payload["quality_score"] == 0.98

    def test_skips_already_succeeded_job(self):
        """Test that already-succeeded jobs are skipped and message is deleted."""
        mock_supabase = MagicMock()
        jobs_table = MagicMock()
        mock_supabase.table.side_effect = lambda name: jobs_table

        select_chain = MagicMock()
        jobs_table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MockTableResponse(data={"status": "SUCCEEDED"})

        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase)

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Should NOT attempt to update or download
        jobs_table.update.assert_not_called()
        mock_s3.get_object.assert_not_called()

        # Should delete the message
        mock_sqs.delete_message.assert_called_once()

    def test_missing_receipt_handle_skips(self):
        """Test that messages without a receipt handle are skipped."""
        mock_supabase = MagicMock()
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase)

        message = {"Body": json.dumps(_make_valid_body())}
        worker._handle_message(message)

        mock_supabase.table.assert_not_called()
        mock_sqs.delete_message.assert_not_called()

    def test_missing_required_fields_marks_failure(self):
        """Test that messages missing required fields trigger failure handling."""
        mock_supabase = MagicMock()
        jobs_table = MagicMock()
        mock_supabase.table.side_effect = lambda name: jobs_table

        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase)

        # Missing s3_key
        body = {"job_id": TEST_JOB_ID, "user_id": TEST_USER_ID}
        message = _make_sqs_message(body)
        worker._handle_message(message)

        # Message should NOT be deleted (failure path)
        mock_sqs.delete_message.assert_not_called()

    def test_s3_download_failure_marks_job_failed(self):
        """Test that S3 download failure marks the job as FAILED."""
        from botocore.exceptions import ClientError

        mock_supabase = MagicMock()
        jobs_table, _ = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase)

        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        # Job should have been updated to RUNNING, then to FAILED
        update_calls = jobs_table.update.call_args_list
        assert len(update_calls) == 2
        assert update_calls[0][0][0]["status"] == "RUNNING"
        assert update_calls[1][0][0]["status"] == "FAILED"
        assert "WORKER_ERROR" in update_calls[1][0][0]["error_code"]

        # Message should NOT be deleted on failure
        mock_sqs.delete_message.assert_not_called()

    @patch("app.worker.enrollment_worker.EmbeddingExtractor")
    def test_no_face_detected_marks_specific_error(self, mock_extractor_cls):
        """Test that NoFaceDetectedError results in NO_FACE_DETECTED error code."""
        mock_supabase = MagicMock()
        jobs_table, _ = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v1")

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        mock_instance = MagicMock()
        mock_extractor_cls.get_instance.return_value = mock_instance
        mock_instance.extract_embedding.side_effect = NoFaceDetectedError("No face")

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        update_calls = jobs_table.update.call_args_list
        failed_call = update_calls[-1][0][0]
        assert failed_call["status"] == "FAILED"
        assert failed_call["error_code"] == "NO_FACE_DETECTED"

    @patch("app.worker.enrollment_worker.EmbeddingExtractor")
    def test_multiple_faces_detected_marks_specific_error(self, mock_extractor_cls):
        """Test that MultipleFacesDetectedError results in MULTIPLE_FACES_DETECTED error code."""
        mock_supabase = MagicMock()
        jobs_table, _ = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase, embedding_mode="v1")

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        mock_instance = MagicMock()
        mock_extractor_cls.get_instance.return_value = mock_instance
        mock_instance.extract_embedding.side_effect = MultipleFacesDetectedError("2 faces")

        message = _make_sqs_message(_make_valid_body())
        worker._handle_message(message)

        update_calls = jobs_table.update.call_args_list
        failed_call = update_calls[-1][0][0]
        assert failed_call["status"] == "FAILED"
        assert failed_call["error_code"] == "MULTIPLE_FACES_DETECTED"


# ============================================================================
# _parse_message_body Tests
# ============================================================================


class TestParseMessageBody:
    """Tests for EnrollmentWorker._parse_message_body()."""

    def test_parse_direct_json(self):
        """Test parsing a direct JSON message body."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase)

        body = json.dumps({"job_id": "123", "user_id": "456"})
        result = worker._parse_message_body(body)
        assert result == {"job_id": "123", "user_id": "456"}

    def test_parse_sns_wrapped_message(self):
        """Test parsing an SNS-wrapped message (has 'Message' key)."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase)

        inner = {"job_id": "123", "user_id": "456"}
        body = json.dumps({"Message": json.dumps(inner)})
        result = worker._parse_message_body(body)
        assert result == inner

    def test_parse_empty_body_raises(self):
        """Test that an empty body raises ValueError."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase)

        with pytest.raises(ValueError, match="Message body is empty"):
            worker._parse_message_body(None)

    def test_parse_non_dict_raises(self):
        """Test that a non-dict JSON body raises ValueError."""
        mock_supabase = MagicMock()
        worker, _, _ = _build_worker(mock_supabase)

        with pytest.raises(ValueError, match="must be a JSON object"):
            worker._parse_message_body(json.dumps([1, 2, 3]))


# ============================================================================
# run() Tests
# ============================================================================


class TestRun:
    """Tests for EnrollmentWorker.run() polling loop."""

    @patch("app.worker.enrollment_worker.time.sleep")
    def test_exits_after_max_empty_polls(self, mock_sleep):
        """Test that the worker exits after max_empty_polls consecutive empty responses."""
        mock_supabase = MagicMock()
        worker, mock_sqs, _ = _build_worker(mock_supabase)
        worker.max_empty_polls = 2
        worker.empty_poll_sleep_seconds = 0

        mock_sqs.receive_message.return_value = {"Messages": []}

        worker.run()

        assert mock_sqs.receive_message.call_count == 2

    @patch("app.worker.enrollment_worker.time.sleep")
    def test_resets_empty_polls_on_messages(self, mock_sleep):
        """Test that empty poll counter resets when messages are received."""
        mock_supabase = MagicMock()
        jobs_table, embeddings_table = _setup_supabase_for_happy_path(mock_supabase)
        worker, mock_sqs, mock_s3 = _build_worker(mock_supabase)
        worker.max_empty_polls = 2
        worker.empty_poll_sleep_seconds = 0

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake-image"
        mock_s3.get_object.return_value = {"Body": mock_body}

        message = _make_sqs_message(_make_valid_body())

        # empty, message, empty, empty -> exits after 2 consecutive empties
        mock_sqs.receive_message.side_effect = [
            {"Messages": []},
            {"Messages": [message]},
            {"Messages": []},
            {"Messages": []},
        ]

        worker.run()

        assert mock_sqs.receive_message.call_count == 4


# ============================================================================
# _resolve_embedding_mode Tests
# ============================================================================


class TestResolveEmbeddingMode:
    """Tests for EnrollmentWorker._resolve_embedding_mode()."""

    def test_v0(self):
        from app.worker.enrollment_worker import EnrollmentWorker
        assert EnrollmentWorker._resolve_embedding_mode("v0") == "v0"

    def test_v1(self):
        from app.worker.enrollment_worker import EnrollmentWorker
        assert EnrollmentWorker._resolve_embedding_mode("v1") == "v1"

    def test_v1_uppercase(self):
        from app.worker.enrollment_worker import EnrollmentWorker
        assert EnrollmentWorker._resolve_embedding_mode("V1") == "v1"

    def test_unknown_defaults_to_v1(self):
        from app.worker.enrollment_worker import EnrollmentWorker
        assert EnrollmentWorker._resolve_embedding_mode("bogus") == "v1"

    def test_empty_defaults_to_v1(self):
        from app.worker.enrollment_worker import EnrollmentWorker
        assert EnrollmentWorker._resolve_embedding_mode("") == "v1"
