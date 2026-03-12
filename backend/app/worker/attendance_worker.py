"""
Attendance worker for processing class photos and generating attendance results.

This worker:
1. Polls the SQS attendance queue for ATTENDANCE jobs
2. Downloads the class photo from S3
3. Detects all faces and extracts embeddings
4. Matches faces against enrolled students using cosine similarity
5. Writes attendance_results to the database
6. Updates the job status with summary fields

Run as a separate process from the main FastAPI server:
    python -m app.worker.attendance_worker
"""

import hashlib
import json
import logging
import math
import random
import time
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from supabase import Client

from app.core.config import get_settings
from app.db.aws import get_s3_client, get_sqs_client
from app.db.supabase import get_supabase_client
from app.models.job import JobStatus
from app.services.recognition_service import (
    FaceMatch,
    NoEnrolledStudentsError,
    RecognitionService,
    RecognitionServiceError,
)
from app.utils.embedding_extractor import (
    DetectedFace,
    EmbeddingExtractor,
    NoFaceDetectedError,
)

logger = logging.getLogger("uvicorn.error")


class AttendanceWorker:
    """
    Worker that processes ATTENDANCE jobs from an SQS queue.

    Message format expected:
    {
        "job_id": "uuid",
        "user_id": "instructor-uuid",
        "class_id": "class-uuid",
        "s3_bucket": "bucket-name",
        "s3_key": "path/to/photo.jpg"
    }

    Processing steps:
    1. Download image from S3
    2. Detect all faces using InsightFace
    3. Match faces against enrolled student embeddings
    4. Write attendance_results rows (one per detected face)
    5. Mark job as SUCCEEDED with summary (present_count, unknown_count)
    """

    def __init__(
        self,
        client: Client | None = None,
        recognition_service: RecognitionService | None = None,
    ) -> None:
        settings = get_settings()

        if not settings.sqs_attendance_queue_url:
            raise ValueError(
                "Missing SQS_ATTENDANCE_QUEUE_URL in backend/.env. "
                "Set it to your attendance queue URL before running worker."
            )

        self.queue_url = settings.sqs_attendance_queue_url
        self.default_bucket = settings.s3_attendance_bucket
        self.max_messages = settings.sqs_max_messages
        self.wait_time_seconds = settings.sqs_wait_time_seconds
        self.max_empty_polls = settings.worker_max_empty_polls
        self.empty_poll_sleep_seconds = settings.worker_poll_sleep_seconds

        self.sqs_client = get_sqs_client()
        self.s3_client = get_s3_client()
        self.supabase = client or get_supabase_client()
        self.recognition_service = recognition_service or RecognitionService(
            client=self.supabase
        )
        self.embedding_mode = self._resolve_embedding_mode(
            settings.worker_embedding_mode
        )

    def run(self) -> None:
        """Main worker loop: poll SQS, process messages, repeat."""
        empty_polls = 0
        logger.info("Starting attendance worker")

        while self.max_empty_polls <= 0 or empty_polls < self.max_empty_polls:
            messages = self._receive_messages()
            if not messages:
                empty_polls += 1
                time.sleep(self.empty_poll_sleep_seconds)
                continue

            empty_polls = 0
            for message in messages:
                self._handle_message(message)

        logger.info("No messages after %s polls; exiting", self.max_empty_polls)

    def _receive_messages(self) -> list[dict[str, Any]]:
        """Poll SQS for messages."""
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time_seconds,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("SQS receive failed: %s", exc)
            return []

        return response.get("Messages", [])

    def _handle_message(self, message: dict[str, Any]) -> None:
        """
        Process a single SQS message.

        This is the main entry point for processing an attendance job.
        """
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            logger.error("Missing receipt handle; skipping message")
            return

        job_id: str | None = None
        try:
            # Parse message payload
            payload = self._parse_message_body(message.get("Body"))
            job_id = payload.get("job_id")
            user_id = payload.get("user_id")
            class_id = payload.get("class_id")
            s3_bucket = payload.get("s3_bucket") or self.default_bucket
            s3_key = payload.get("s3_key")

            if not job_id or not user_id or not class_id or not s3_key:
                raise ValueError(
                    "Missing required fields in message body "
                    "(need job_id, user_id, class_id, s3_key)"
                )

            # Check if job already succeeded (idempotency)
            existing_status = self._get_job_status(job_id)
            if existing_status == JobStatus.SUCCEEDED:
                logger.info("Job %s already succeeded; deleting message", job_id)
                self._delete_message(receipt_handle)
                return

            # Mark job as RUNNING
            self._update_job_status(job_id, JobStatus.RUNNING)

            # Get session_id for this job (required to write attendance_results)
            session_id = self._get_session_id_for_job(job_id)
            if not session_id:
                raise ValueError(f"No attendance session found for job {job_id}")

            # Process the attendance photo
            logger.info(
                "Processing attendance job %s for class %s", job_id, class_id
            )

            # Step 1: Download image from S3
            image_bytes = self._download_image(s3_bucket, s3_key)

            # Step 2: Detect faces and extract embeddings
            if self.embedding_mode == "v0":
                # Stub mode for testing: generate fake face detections
                detected_faces = _generate_stub_faces(job_id, count=3)
            else:
                detected_faces = self._detect_faces(image_bytes)

            # Step 3: Match faces against enrolled students
            matches, summary = self.recognition_service.recognize_class_photo(
                detected_faces, class_id
            )

            # Step 4: Write attendance_results to database
            self._write_attendance_results(session_id, matches)

            # Step 5: Mark job as SUCCEEDED with summary
            self._update_job_status(
                job_id,
                JobStatus.SUCCEEDED,
                present_count=summary["present_count"],
                unknown_count=summary["unknown_count"],
            )

            # Delete message from queue
            self._delete_message(receipt_handle)

            logger.info(
                "Attendance job %s completed: %d present, %d unknown",
                job_id, summary["present_count"], summary["unknown_count"]
            )

        except NoFaceDetectedError as exc:
            self._handle_failure(job_id, receipt_handle, "NO_FACES_DETECTED", exc)
        except NoEnrolledStudentsError as exc:
            self._handle_failure(job_id, receipt_handle, "NO_ENROLLED_STUDENTS", exc)
        except RecognitionServiceError as exc:
            self._handle_failure(job_id, receipt_handle, "RECOGNITION_ERROR", exc)
        except Exception as exc:
            self._handle_failure(job_id, receipt_handle, "WORKER_ERROR", exc)

    def _parse_message_body(self, body: str | None) -> dict[str, Any]:
        """Parse SQS message body (handles both direct and SNS-wrapped formats)."""
        if not body:
            raise ValueError("Message body is empty")

        payload = json.loads(body)

        # Handle SNS wrapper (if message came via SNS)
        if isinstance(payload, dict) and "Message" in payload:
            return json.loads(payload["Message"])

        if not isinstance(payload, dict):
            raise ValueError("Message body must be a JSON object")

        return payload

    def _download_image(self, bucket: str, key: str) -> bytes:
        """Download image from S3."""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 download failed: {exc}") from exc

    def _detect_faces(self, image_bytes: bytes) -> list[DetectedFace]:
        """
        Detect all faces in an image and extract embeddings.

        Uses InsightFace for detection and ArcFace for embedding extraction.
        """
        extractor = EmbeddingExtractor.get_instance()
        # min_quality=0.5 filters out low-confidence face detections
        return extractor.extract_multiple_embeddings(image_bytes, min_quality=0.5)

    def _get_job_status(self, job_id: str) -> str | None:
        """Get current job status from database."""
        try:
            result = (
                self.supabase.table("jobs")
                .select("status")
                .eq("id", job_id)
                .single()
                .execute()
            )
            if not result.data:
                return None
            return result.data.get("status")
        except Exception:
            return None

    def _get_session_id_for_job(self, job_id: str) -> str | None:
        """Get the attendance_session ID linked to this job."""
        try:
            result = (
                self.supabase.table("attendance_sessions")
                .select("id")
                .eq("job_id", job_id)
                .single()
                .execute()
            )
            if not result.data:
                return None
            return result.data.get("id")
        except Exception:
            return None

    def _update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
        present_count: int | None = None,
        unknown_count: int | None = None,
    ) -> None:
        """Update job status and optional summary fields."""
        payload: dict[str, Any] = {"status": status}

        if error_message is not None:
            payload["error_message"] = error_message
        if present_count is not None:
            payload["present_count"] = present_count
        if unknown_count is not None:
            payload["unknown_count"] = unknown_count

        result = (
            self.supabase.table("jobs")
            .update(payload)
            .eq("id", job_id)
            .execute()
        )
        if result.data is None:
            raise RuntimeError(f"Failed to update job {job_id} status to {status}")

    def _write_attendance_results(
        self, session_id: str, matches: list[FaceMatch]
    ) -> None:
        """
        Write attendance results to the database.

        Each detected face gets a row in attendance_results:
        - student_id: matched student UUID, or NULL for UNKNOWN faces
        - confidence: cosine similarity score
        - face_index: position in the original detection order
        """
        rows = [
            {
                "session_id": session_id,
                "student_id": match.student_id,  # None for UNKNOWN
                "confidence": match.confidence,
                "face_index": match.face_index,
            }
            for match in matches
        ]

        if not rows:
            logger.warning("No attendance results to write for session %s", session_id)
            return

        result = (
            self.supabase.table("attendance_results")
            .insert(rows)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                f"Failed to insert attendance results for session {session_id}"
            )

        logger.info(
            "Wrote %d attendance results for session %s", len(rows), session_id
        )

    def _delete_message(self, receipt_handle: str) -> None:
        """Delete processed message from SQS queue."""
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("Failed to delete message: %s", exc)

    def _handle_failure(
        self,
        job_id: str | None,
        receipt_handle: str,
        error_code: str,
        exc: Exception,
    ) -> None:
        """Handle job failure: log, update status, but don't delete message."""
        error_message = f"{error_code}: {exc}"
        logger.exception("Failed to process attendance job %s", job_id or "<unknown>")

        if job_id:
            try:
                self._update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=error_message,
                )
            except Exception as update_exc:
                logger.error(
                    "Failed to mark job %s as failed: %s", job_id, update_exc
                )

        # Don't delete message on failure - allow SQS retry or DLQ

    @staticmethod
    def _resolve_embedding_mode(value: str) -> str:
        """Resolve embedding mode from config."""
        normalized = (value or "").strip().lower()
        if normalized in {"v0", "v1"}:
            return normalized
        logger.warning(
            "Unknown WORKER_EMBEDDING_MODE=%s, defaulting to v1", value
        )
        return "v1"


def _generate_stub_faces(seed_value: str, count: int = 3) -> list[DetectedFace]:
    """
    Generate stub face detections for testing (v0 mode).

    Creates deterministic fake embeddings based on the seed value.
    """
    from app.utils.embedding_extractor import DetectedFace

    seed = int(hashlib.sha256(seed_value.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    faces = []
    for i in range(count):
        # Generate normalized 512-dim embedding
        values = [rng.uniform(-1.0, 1.0) for _ in range(512)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        embedding = [v / norm for v in values]

        faces.append(
            DetectedFace(
                embedding=embedding,
                quality_score=rng.uniform(0.7, 0.99),
                face_index=i,
                bbox=(i * 100, 50, i * 100 + 80, 130),
            )
        )

    return faces


# Entry point for running as a standalone process
if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    worker = AttendanceWorker()
    worker.run()
