import json
from unittest.mock import MagicMock

import pytest

from app.services.queue_service import QueueService, QueueServiceError


class TestQueueService:
    """Tests for QueueService.send_message."""

    def test_send_message_success(self):
        """Happy path: message is sent with correct JSON body."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {
            "MessageId": "msg-123",
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

        service = QueueService(sqs_client=mock_sqs)
        body = {"job_id": "abc", "user_id": "def", "bucket": "b", "key": "k"}
        result = service.send_message("https://sqs.us-east-1.amazonaws.com/123/test-queue", body)

        mock_sqs.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123/test-queue",
            MessageBody=json.dumps(body),
        )
        assert result["MessageId"] == "msg-123"

    def test_send_message_serializes_as_json(self):
        """Message body should be JSON-serialized."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {"MessageId": "msg-456"}

        service = QueueService(sqs_client=mock_sqs)
        service.send_message("https://queue-url", {"key": "value"})

        call_args = mock_sqs.send_message.call_args
        parsed = json.loads(call_args.kwargs["MessageBody"])
        assert parsed == {"key": "value"}

    def test_send_message_raises_on_boto3_error(self):
        """Boto3 errors should be wrapped in QueueServiceError."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = Exception("Connection refused")

        service = QueueService(sqs_client=mock_sqs)
        with pytest.raises(QueueServiceError, match="Failed to send SQS message"):
            service.send_message("https://queue-url", {"key": "value"})
