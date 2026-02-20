from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.schemas.job import CreateJobRequest
from app.services.job_service import JobService, CreateJobError
from app.services.queue_service import QueueServiceError


TEST_USER_ID = "12345678-1234-1234-1234-123456789012"
TEST_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TEST_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/faceit-enrollment-queue"
TEST_BUCKET = "faceit-uploads-dev"


def make_request(
    bucket: str = TEST_BUCKET,
    key: str = f"enrollment-photos/{TEST_USER_ID}/abcdef01-2345-6789-abcd-ef0123456789.jpg",
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
        """Key must start with enrollment-photos/{authenticated_user_id}/."""
        mock_get_settings.return_value = make_mock_settings()

        other_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        key = f"enrollment-photos/{other_user_id}/abcdef01-2345-6789-abcd-ef0123456789.jpg"

        service = JobService(client=MagicMock(), queue_service=MagicMock())
        with pytest.raises(CreateJobError, match="does not belong to the authenticated user"):
            await service.create_enrollment_job(
                make_request(key=key), TEST_USER_ID
            )
