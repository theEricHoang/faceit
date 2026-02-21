import hashlib
import json
import logging
import math
import random
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from supabase import Client

from app.core.config import get_settings
from app.db.supabase import get_supabase_client

LOGGER = logging.getLogger(__name__)


class EnrollmentWorker:
    def __init__(self, client: Client | None = None) -> None:
        settings = get_settings()
        if settings.aws_profile:
            session = boto3.Session(profile_name=settings.aws_profile)
        else:
            session = boto3.Session()

        if not settings.sqs_enrollment_queue_url:
            raise ValueError(
                "Missing SQS_ENROLLMENT_QUEUE_URL in backend/.env. "
                "Set it to your enrollment queue URL before running worker/smoke tests."
            )

        self.queue_url = settings.sqs_enrollment_queue_url
        self.default_bucket = settings.s3_enrollment_bucket
        self.max_messages = settings.sqs_max_messages
        self.wait_time_seconds = settings.sqs_wait_time_seconds
        self.max_empty_polls = settings.worker_max_empty_polls
        self.empty_poll_sleep_seconds = settings.worker_poll_sleep_seconds

        self.sqs_client = session.client("sqs", region_name=settings.aws_region)
        self.s3_client = session.client("s3", region_name=settings.aws_region)
        self.supabase = client or get_supabase_client()

    def run(self) -> None:
        empty_polls = 0
        LOGGER.info("Starting enrollment worker")

        while empty_polls < self.max_empty_polls:
            messages = self._receive_messages()
            if not messages:
                empty_polls += 1
                time.sleep(self.empty_poll_sleep_seconds)
                continue

            empty_polls = 0
            for message in messages:
                self._handle_message(message)

        LOGGER.info("No messages after %s polls; exiting", self.max_empty_polls)

    def _receive_messages(self) -> list[dict[str, Any]]:
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time_seconds,
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.error("SQS receive failed: %s", exc)
            return []

        return response.get("Messages", [])

    def _handle_message(self, message: dict[str, Any]) -> None:
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            LOGGER.error("Missing receipt handle; skipping message")
            return

        job_id: str | None = None
        try:
            payload = self._parse_message_body(message.get("Body"))
            job_id = payload.get("job_id")
            user_id = payload.get("user_id")
            s3_bucket = payload.get("s3_bucket") or self.default_bucket
            s3_key = payload.get("s3_key")

            if not job_id or not user_id or not s3_key:
                raise ValueError("Missing required fields in message body")

            existing_status = self._get_job_status(job_id)
            if isinstance(existing_status, str) and existing_status.lower() == "succeeded":
                LOGGER.info("Job already succeeded; deleting message %s", job_id)
                self._delete_message(receipt_handle)
                return

            self._update_job_status(job_id, "running")

            self._download_image(s3_bucket, s3_key)
            embedding = generate_stub_embedding(job_id)

            self._insert_embedding(user_id=user_id, embedding=embedding)
            self._update_job_status(job_id, "succeeded")
            self._delete_message(receipt_handle)
        except Exception as exc:
            error_message = f"WORKER_ERROR: {exc}"
            LOGGER.exception("Failed to process job %s", job_id or "<unknown>")
            if job_id:
                try:
                    self._update_job_status(job_id, "failed", error_message=error_message)
                except Exception as update_exc:
                    LOGGER.error("Failed to mark job %s as failed: %s", job_id, update_exc)
            self._delete_message(receipt_handle)

    def _parse_message_body(self, body: str | None) -> dict[str, Any]:
        if not body:
            raise ValueError("Message body is empty")

        payload = json.loads(body)
        if isinstance(payload, dict) and "Message" in payload:
            return json.loads(payload["Message"])
        if not isinstance(payload, dict):
            raise ValueError("Message body must be a JSON object")
        return payload

    def _download_image(self, bucket: str, key: str) -> None:
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            _ = response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 download failed: {exc}")

    def _get_job_status(self, job_id: str) -> str | None:
        result = (
            self.supabase
            .table("jobs")
            .select("status")
            .eq("id", job_id)
            .single()
            .execute()
        )
        if not result.data:
            return None
        return result.data.get("status")

    def _update_job_status(
        self, job_id: str, status: str, error_message: str | None = None
    ) -> None:
        last_exception: Exception | None = None
        for status_value in _enum_variants(status):
            payload: dict[str, Any] = {"status": status_value}
            if error_message is not None:
                payload["error_message"] = error_message

            try:
                result = (
                    self.supabase
                    .table("jobs")
                    .update(payload)
                    .eq("id", job_id)
                    .execute()
                )
                if result.data is None:
                    raise RuntimeError("Failed to update job status")
                return
            except Exception as exc:
                last_exception = exc

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Failed to update job status")

    def _insert_embedding(self, user_id: str, embedding: list[float]) -> None:
        payload = {
            "user_id": user_id,
            "model": "stub-embedding-v0",
            "embedding": embedding,
            "quality_score": None,
        }
        result = (
            self.supabase
            .table("face_embeddings")
            .insert(payload)
            .execute()
        )
        if result.data is None:
            raise RuntimeError("Failed to insert face embedding")

    def _delete_message(self, receipt_handle: str) -> None:
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.error("Failed to delete message: %s", exc)


def generate_stub_embedding(seed_value: str, size: int = 512) -> list[float]:
    seed = int(hashlib.sha256(seed_value.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    values = [rng.uniform(-1.0, 1.0) for _ in range(size)]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _enum_variants(value: str) -> list[str]:
    variants = [value.upper(), value, value.lower()]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in variants:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    EnrollmentWorker().run()


if __name__ == "__main__":
    main()
