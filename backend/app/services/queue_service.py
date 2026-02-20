import json

import boto3
from botocore.config import Config

from app.core.config import get_settings


class QueueServiceError(Exception):
    pass


class QueueService:
    """Thin wrapper around SQS for sending messages."""

    def __init__(self, sqs_client=None):
        if sqs_client is not None:
            self.sqs_client = sqs_client
        else:
            settings = get_settings()
            if settings.aws_profile:
                session = boto3.Session(profile_name=settings.aws_profile)
            else:
                session = boto3.Session()
            self.sqs_client = session.client(
                "sqs",
                region_name=settings.aws_region,
                config=Config(retries={"max_attempts": 3, "mode": "standard"}),
            )

    def send_message(self, queue_url: str, message_body: dict) -> dict:
        """Send a JSON message to an SQS queue.

        Args:
            queue_url: The URL of the SQS queue.
            message_body: Dict to be JSON-serialized as the message body.

        Returns:
            The SQS SendMessage response.

        Raises:
            QueueServiceError: If the message could not be sent.
        """
        try:
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body),
            )
            return response
        except Exception as e:
            raise QueueServiceError(f"Failed to send SQS message: {str(e)}") from e
