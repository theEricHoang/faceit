import json

from app.db.aws import get_sqs_client


class QueueServiceError(Exception):
    pass


class QueueService:
    """Thin wrapper around SQS for sending messages."""

    def __init__(self, sqs_client=None):
        self.sqs_client = sqs_client or get_sqs_client()

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
