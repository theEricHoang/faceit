from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.schemas.job import CreateJobRequest
from app.services.job_service import JobService, CreateJobError, JobNotFoundError, JobNotPendingError, JobOwnershipError
from app.services.queue_service import QueueServiceError


TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TEST_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/faceit-enrollment-queue"
TEST_ATTENDANCE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/faceit-attendance-queue"
TEST_BUCKET = "faceit-uploads-dev"
TEST_CLASS_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
TEST_SESSION_ID = "99999999-9999-9999-9999-999999999999"


def make_request(
    bucket: str = TEST_BUCKET,
    key: str = f"enrollments/{TEST_USER_ID}/abcdef01-2345-6789-abcd-ef0123456789.jpg",
) -> CreateJobRequest:
    return CreateJobRequest(kind="ENROLLMENT", bucket=bucket, key=key)


def make_mock_settings():
    return MagicMock(
        sqs_enrollment_queue_url=TEST_QUEUE_URL,
        s3_enrollment_bucket=TEST_BUCKET,
    )


def make_mock_supabase(job_id: str = TEST_JOB_ID) -> MagicMock:
    """Create a mock Supabase client with a jobs table insert chain."""
    client = MagicMock()
    table = MagicMock()
    insert_chain = MagicMock()
    delete_chain = MagicMock()

    client.table.return_value = table
    table.insert.return_value = insert_chain
    insert_chain.execute.return_value = MagicMock(data=[{"id": job_id}])

    table.delete.return_value = delete_chain
    delete_chain.eq.return_value = delete_chain
    delete_chain.execute.return_value = MagicMock(data=[])

    return client


class TestCreateEnrollmentJob:
    """Tests for JobService.create_enrollment_job."""

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_happy_path_returns_job_id(self, mock_get_settings):
        """Successful creation returns job_id."""
        mock_get_settings.return_value = make_mock_settings()

        mock_client = make_mock_supabase()
        mock_queue = MagicMock()
        mock_queue.send_message.return_value = {"MessageId": "msg-1"}

        service = JobService(client=mock_client, queue_service=mock_queue)
        result = await service.create_enrollment_job(make_request(), TEST_USER_ID)

        assert result.job_id == UUID(TEST_JOB_ID)

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_inserts_pending_job_row(self, mock_get_settings):
        """Should insert a PENDING row with correct fields."""
        mock_get_settings.return_value = make_mock_settings()

        mock_client = make_mock_supabase()
        mock_queue = MagicMock()

        request = make_request()
        service = JobService(client=mock_client, queue_service=mock_queue)
        await service.create_enrollment_job(request, TEST_USER_ID)

        mock_client.table.assert_any_call("jobs")
        insert_args = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_args["kind"] == "ENROLLMENT"
        assert insert_args["status"] == "PENDING"
        assert insert_args["owner_user_id"] == TEST_USER_ID
        assert insert_args["s3_bucket"] == TEST_BUCKET
        assert insert_args["s3_key"] == request.key

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_sends_sqs_message_with_correct_body(self, mock_get_settings):
        """Should send SQS message containing job_id, user_id, bucket, key."""
        mock_get_settings.return_value = make_mock_settings()

        mock_client = make_mock_supabase()
        mock_queue = MagicMock()

        request = make_request()
        service = JobService(client=mock_client, queue_service=mock_queue)
        await service.create_enrollment_job(request, TEST_USER_ID)

        mock_queue.send_message.assert_called_once()
        call_kwargs = mock_queue.send_message.call_args.kwargs
        assert call_kwargs["queue_url"] == TEST_QUEUE_URL
        body = call_kwargs["message_body"]
        assert body["job_id"] == TEST_JOB_ID
        assert body["user_id"] == TEST_USER_ID
        assert body["bucket"] == TEST_BUCKET
        assert body["key"] == request.key

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_supabase_insert_fails_raises_create_job_error(self, mock_get_settings):
        """If DB insert fails, raise CreateJobError (no rollback needed)."""
        mock_get_settings.return_value = make_mock_settings()

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "DB connection error"
        )
        mock_queue = MagicMock()

        service = JobService(client=mock_client, queue_service=mock_queue)
        with pytest.raises(CreateJobError, match="Failed to create job"):
            await service.create_enrollment_job(make_request(), TEST_USER_ID)

        # SQS should not have been called
        mock_queue.send_message.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_sqs_fails_rolls_back_job_row(self, mock_get_settings):
        """If SQS send fails after DB insert, the jobs row should be deleted."""
        mock_get_settings.return_value = make_mock_settings()

        mock_client = make_mock_supabase()
        mock_queue = MagicMock()
        mock_queue.send_message.side_effect = QueueServiceError("SQS unavailable")

        service = JobService(client=mock_client, queue_service=mock_queue)
        with pytest.raises(CreateJobError, match="Failed to enqueue job"):
            await service.create_enrollment_job(make_request(), TEST_USER_ID)

        # Verify rollback: delete was called with the job_id
        delete_chain = mock_client.table.return_value.delete.return_value
        delete_chain.eq.assert_called_with("id", TEST_JOB_ID)
        delete_chain.eq.return_value.execute.assert_called_once()


class TestCreateEnrollmentJobValidation:
    """Tests for input validation in JobService.create_enrollment_job."""

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_wrong_bucket_raises_create_job_error(self, mock_get_settings):
        """Bucket must match the configured s3_enrollment_bucket."""
        mock_get_settings.return_value = make_mock_settings()

        service = JobService(client=MagicMock(), queue_service=MagicMock())
        with pytest.raises(CreateJobError, match="Invalid bucket"):
            await service.create_enrollment_job(
                make_request(bucket="evil-bucket"), TEST_USER_ID
            )

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_invalid_key_format_raises_create_job_error(self, mock_get_settings):
        """Key must match the enrollment-photos/<user_id>/<uuid>.<ext> pattern."""
        mock_get_settings.return_value = make_mock_settings()

        service = JobService(client=MagicMock(), queue_service=MagicMock())
        with pytest.raises(CreateJobError, match="Invalid key format"):
            await service.create_enrollment_job(
                make_request(key="../../etc/passwd"), TEST_USER_ID
            )

    @pytest.mark.asyncio
    @patch("app.services.job_service.get_settings")
    async def test_key_for_other_user_raises_create_job_error(self, mock_get_settings):
        """Key must start with enrollments/{authenticated_user_id}/."""
        mock_get_settings.return_value = make_mock_settings()

        other_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        key = f"enrollments/{other_user_id}/abcdef01-2345-6789-abcd-ef0123456789.jpg"

        service = JobService(client=MagicMock(), queue_service=MagicMock())
        with pytest.raises(CreateJobError, match="does not belong to the authenticated user"):
            await service.create_enrollment_job(
                make_request(key=key), TEST_USER_ID
            )


class TestGetJobStatus:
    """Tests for JobService.get_job_status."""

    @pytest.mark.asyncio
    async def test_returns_job_status_response(self):
        """Successful query returns a JobStatusResponse with correct fields."""
        mock_client = MagicMock()
        table = MagicMock()
        select_chain = MagicMock()

        mock_client.table.return_value = table
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MagicMock(
            data={
                "id": TEST_JOB_ID,
                "kind": "ENROLLMENT",
                "status": "SUCCEEDED",
                "error_message": None,
                "updated_at": "2026-03-04T12:00:00Z",
            }
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        result = await service.get_job_status(
            UUID(TEST_JOB_ID), UUID(TEST_USER_ID)
        )

        assert result.job_id == UUID(TEST_JOB_ID)
        assert result.status == "SUCCEEDED"
        assert result.kind == "ENROLLMENT"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_failed_job_includes_error_message(self):
        """A FAILED job should include the error_message."""
        mock_client = MagicMock()
        table = MagicMock()
        select_chain = MagicMock()

        mock_client.table.return_value = table
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MagicMock(
            data={
                "id": TEST_JOB_ID,
                "kind": "ENROLLMENT",
                "status": "FAILED",
                "error_message": "NO_FACE_DETECTED: no face found in image",
                "updated_at": "2026-03-04T12:00:00Z",
            }
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        result = await service.get_job_status(
            UUID(TEST_JOB_ID), UUID(TEST_USER_ID)
        )

        assert result.status == "FAILED"
        assert result.error_message == "NO_FACE_DETECTED: no face found in image"

    @pytest.mark.asyncio
    async def test_queries_with_both_job_id_and_owner(self):
        """Should filter by both id and owner_user_id in the query."""
        mock_client = MagicMock()
        table = MagicMock()
        select_chain = MagicMock()

        mock_client.table.return_value = table
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.return_value = MagicMock(
            data={
                "id": TEST_JOB_ID,
                "kind": "ENROLLMENT",
                "status": "PENDING",
                "error_message": None,
                "present_count": None,
                "unknown_count": None,
                "updated_at": "2026-03-04T12:00:00Z",
            }
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        await service.get_job_status(UUID(TEST_JOB_ID), UUID(TEST_USER_ID))

        mock_client.table.assert_called_with("jobs")
        table.select.assert_called_once_with(
            "id, kind, status, error_message, present_count, unknown_count, updated_at"
        )
        # eq is called twice: once for id, once for owner_user_id
        eq_calls = select_chain.eq.call_args_list
        assert len(eq_calls) == 2
        assert eq_calls[0].args == ("id", TEST_JOB_ID)
        assert eq_calls[1].args == ("owner_user_id", TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_not_found_raises_job_not_found_error(self):
        """When Supabase .single() raises (no row), should raise JobNotFoundError."""
        mock_client = MagicMock()
        table = MagicMock()
        select_chain = MagicMock()

        mock_client.table.return_value = table
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.side_effect = Exception("Row not found")

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(JobNotFoundError, match="not found"):
            await service.get_job_status(
                UUID(TEST_JOB_ID), UUID(TEST_USER_ID)
            )

    @pytest.mark.asyncio
    async def test_wrong_owner_raises_job_not_found_error(self):
        """Query filters by owner, so wrong owner = exception from .single() = not found."""
        other_user_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_client = MagicMock()
        table = MagicMock()
        select_chain = MagicMock()

        mock_client.table.return_value = table
        table.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.single.return_value = select_chain
        select_chain.execute.side_effect = Exception("Row not found")

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(JobNotFoundError, match="not found"):
            await service.get_job_status(UUID(TEST_JOB_ID), other_user_id)


# ===========================================================================
# Attendance Job Tests
# ===========================================================================


class TestCreatePendingAttendanceJob:
    """Tests for JobService.create_pending_attendance_job."""

    def test_happy_path_creates_pending_attendance_job(self):
        """Inserts row with kind=ATTENDANCE, status=PENDING and returns job row."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{
                "id": TEST_JOB_ID,
                "kind": "ATTENDANCE",
                "status": "PENDING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            }]
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        result = service.create_pending_attendance_job(
            job_id=TEST_JOB_ID,
            user_id=TEST_USER_ID,
            bucket=TEST_BUCKET,
            key="attendance-photos/test.jpg",
        )

        assert result["id"] == TEST_JOB_ID
        assert result["kind"] == "ATTENDANCE"
        assert result["status"] == "PENDING"
        assert result["owner_user_id"] == TEST_USER_ID
        assert result["s3_bucket"] == TEST_BUCKET

        # Verify the insert was called with correct data
        insert_args = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_args["kind"] == "ATTENDANCE"
        assert insert_args["status"] == "PENDING"
        assert insert_args["owner_user_id"] == TEST_USER_ID
        assert insert_args["s3_bucket"] == TEST_BUCKET
        assert insert_args["s3_key"] == "attendance-photos/test.jpg"

    def test_db_insert_fails_raises_create_job_error(self):
        """DB exception is wrapped in CreateJobError."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "DB connection error"
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(CreateJobError, match="Failed to create attendance job"):
            service.create_pending_attendance_job(
                job_id=TEST_JOB_ID,
                user_id=TEST_USER_ID,
                bucket=TEST_BUCKET,
                key="attendance-photos/test.jpg",
            )


def _make_enqueue_attendance_mock_client(
    job_data=None,
    job_select_side_effect=None,
):
    """Build a mock Supabase client for enqueue_attendance_job tests.

    Since enqueue_attendance_job no longer queries attendance_sessions,
    only the jobs table routing is needed.
    """
    client = MagicMock()

    # Jobs select chain
    job_chain = MagicMock()
    job_chain.select.return_value = job_chain
    job_chain.eq.return_value = job_chain
    job_chain.single.return_value = job_chain

    if job_select_side_effect:
        job_chain.execute.side_effect = job_select_side_effect
    else:
        job_chain.execute.return_value = MagicMock(data=job_data)

    # Update chain for QUEUED status transition
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=[])
    job_chain.update.return_value = update_chain

    client.table.return_value = job_chain
    return client


class TestEnqueueAttendanceJob:
    """Tests for JobService.enqueue_attendance_job."""

    @patch("app.services.job_service.get_settings")
    def test_happy_path_enqueues_and_returns_response(self, mock_get_settings):
        """Retrieves PENDING job, sends SQS, returns response."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "PENDING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )
        mock_queue = MagicMock()
        mock_queue.send_message.return_value = {"MessageId": "msg-1"}

        service = JobService(client=mock_client, queue_service=mock_queue)
        result = service.enqueue_attendance_job(
            job_id=TEST_JOB_ID,
            user_id=TEST_USER_ID,
            class_id=TEST_CLASS_ID,
            session_id=TEST_SESSION_ID,
        )

        assert str(result.job_id) == TEST_JOB_ID
        assert str(result.session_id) == TEST_SESSION_ID

    @patch("app.services.job_service.get_settings")
    def test_sends_sqs_with_correct_body(self, mock_get_settings):
        """Verifies message body contains job_id, user_id, class_id, s3_bucket, s3_key."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "PENDING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )
        mock_queue = MagicMock()

        service = JobService(client=mock_client, queue_service=mock_queue)
        service.enqueue_attendance_job(
            job_id=TEST_JOB_ID,
            user_id=TEST_USER_ID,
            class_id=TEST_CLASS_ID,
            session_id=TEST_SESSION_ID,
        )

        mock_queue.send_message.assert_called_once()
        call_kwargs = mock_queue.send_message.call_args.kwargs
        assert call_kwargs["queue_url"] == TEST_ATTENDANCE_QUEUE_URL
        body = call_kwargs["message_body"]
        assert body["job_id"] == TEST_JOB_ID
        assert body["user_id"] == TEST_USER_ID
        assert body["class_id"] == TEST_CLASS_ID
        assert body["session_id"] == TEST_SESSION_ID
        assert body["s3_bucket"] == TEST_BUCKET
        assert body["s3_key"] == "attendance-photos/test.jpg"

    @patch("app.services.job_service.get_settings")
    def test_transitions_job_to_queued_after_sqs_send(self, mock_get_settings):
        """After successful SQS send, job status should be updated to QUEUED."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "PENDING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )
        mock_queue = MagicMock()
        mock_queue.send_message.return_value = {"MessageId": "msg-1"}

        service = JobService(client=mock_client, queue_service=mock_queue)
        service.enqueue_attendance_job(
            job_id=TEST_JOB_ID,
            user_id=TEST_USER_ID,
            class_id=TEST_CLASS_ID,
            session_id=TEST_SESSION_ID,
        )

        # Verify update was called with QUEUED status
        job_table = mock_client.table.return_value
        job_table.update.assert_called_once()
        update_arg = job_table.update.call_args[0][0]
        assert update_arg["status"] == "QUEUED"

    @patch("app.services.job_service.get_settings")
    def test_job_not_found_raises_job_not_found_error(self, mock_get_settings):
        """No row found raises JobNotFoundError."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_select_side_effect=Exception("Row not found"),
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(JobNotFoundError, match="not found"):
            service.enqueue_attendance_job(
                job_id=TEST_JOB_ID,
                user_id=TEST_USER_ID,
                class_id=TEST_CLASS_ID,
                session_id=TEST_SESSION_ID,
            )

    @patch("app.services.job_service.get_settings")
    def test_job_not_pending_raises_job_not_pending_error(self, mock_get_settings):
        """Job in RUNNING status raises JobNotPendingError."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "RUNNING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(JobNotPendingError, match="not in PENDING"):
            service.enqueue_attendance_job(
                job_id=TEST_JOB_ID,
                user_id=TEST_USER_ID,
                class_id=TEST_CLASS_ID,
                session_id=TEST_SESSION_ID,
            )

    @patch("app.services.job_service.get_settings")
    def test_wrong_owner_raises_job_ownership_error(self, mock_get_settings):
        """owner_user_id mismatch raises JobOwnershipError."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        other_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "PENDING",
                "owner_user_id": other_user_id,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )

        service = JobService(client=mock_client, queue_service=MagicMock())
        with pytest.raises(JobOwnershipError, match="does not belong"):
            service.enqueue_attendance_job(
                job_id=TEST_JOB_ID,
                user_id=TEST_USER_ID,
                class_id=TEST_CLASS_ID,
                session_id=TEST_SESSION_ID,
            )

    @patch("app.services.job_service.get_settings")
    def test_sqs_failure_raises_create_job_error(self, mock_get_settings):
        """QueueServiceError is wrapped in CreateJobError."""
        mock_get_settings.return_value = MagicMock(
            sqs_attendance_queue_url=TEST_ATTENDANCE_QUEUE_URL,
        )

        mock_client = _make_enqueue_attendance_mock_client(
            job_data={
                "id": TEST_JOB_ID,
                "status": "PENDING",
                "owner_user_id": TEST_USER_ID,
                "s3_bucket": TEST_BUCKET,
                "s3_key": "attendance-photos/test.jpg",
            },
        )
        mock_queue = MagicMock()
        mock_queue.send_message.side_effect = QueueServiceError("SQS unavailable")

        service = JobService(client=mock_client, queue_service=mock_queue)
        with pytest.raises(CreateJobError, match="Failed to enqueue job"):
            service.enqueue_attendance_job(
                job_id=TEST_JOB_ID,
                user_id=TEST_USER_ID,
                class_id=TEST_CLASS_ID,
                session_id=TEST_SESSION_ID,
            )
