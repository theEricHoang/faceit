"""
Smoke test for the Attendance Worker.

This script tests the complete attendance recognition flow:
1. Creates test data (enrolled students with embeddings)
2. Creates an attendance job with a class photo
3. Runs the worker to process the job
4. Verifies attendance results were written

Usage:
    python -m tests.smoke_test_attendance_worker \
        --class-id <class-uuid> \
        --instructor-id <instructor-uuid> \
        [--bucket <s3-bucket>] \
        [--embedding-mode v0|v1]

NOTE: This requires:
- Valid AWS credentials configured (for S3 and SQS access)
- Existing data in the database:
  - A class with students enrolled (student_classes)
  - Face embeddings for enrolled students (face_embeddings)
- Environment variables set in backend/.env
"""

import argparse
import json
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.db.aws import get_s3_client, get_sqs_client
from app.db.supabase import get_supabase_client
from app.worker.attendance_worker import AttendanceWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("smoke_test_attendance")


@dataclass
class SmokeResult:
    passed: bool
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end smoke test for attendance worker."
    )
    parser.add_argument(
        "--class-id",
        required=True,
        help="Class UUID that has enrolled students with embeddings.",
    )
    parser.add_argument(
        "--instructor-id",
        required=True,
        help="Instructor UUID (owner of the class and job).",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Optional S3 bucket override (defaults to S3_ATTENDANCE_BUCKET).",
    )
    parser.add_argument(
        "--embedding-mode",
        default="v0",
        choices=["v0", "v1"],
        help="Worker embedding mode (v0=stub for testing, v1=real InsightFace).",
    )
    parser.add_argument(
        "--image-path",
        default=None,
        help="Optional path to a real class photo (for v1 mode testing).",
    )
    return parser.parse_args()


def upload_test_image(s3_client, bucket: str, key: str, image_path: str | None) -> None:
    """Upload a test image to S3."""
    if image_path:
        # Use real image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    else:
        # Create a minimal JPEG-like placeholder
        image_bytes = b"\xff\xd8\xff\xe0SMOKE_TEST_ATTENDANCE\xff\xd9"

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
    )
    logger.info("Uploaded test image to s3://%s/%s", bucket, key)


def create_attendance_job(supabase, job_id: str, owner_id: str, bucket: str, key: str) -> None:
    """Create a PENDING attendance job in the database."""
    result = (
        supabase.table("jobs")
        .insert({
            "id": job_id,
            "kind": "ATTENDANCE",
            "status": "PENDING",
            "owner_user_id": owner_id,
            "s3_bucket": bucket,
            "s3_key": key,
        })
        .execute()
    )
    if not result.data:
        raise RuntimeError("Failed to create job")
    logger.info("Created attendance job %s", job_id)


def create_attendance_session(
    supabase, session_id: str, class_id: str, instructor_id: str, job_id: str
) -> None:
    """Create an attendance session linked to the job."""
    result = (
        supabase.table("attendance_sessions")
        .insert({
            "id": session_id,
            "class_id": class_id,
            "instructor_id": instructor_id,
            "job_id": job_id,
        })
        .execute()
    )
    if not result.data:
        raise RuntimeError("Failed to create attendance session")
    logger.info("Created attendance session %s", session_id)


def enqueue_attendance_message(
    sqs_client, queue_url: str, job_id: str, user_id: str, class_id: str, bucket: str, key: str
) -> None:
    """Send a message to the attendance SQS queue."""
    message_body = {
        "job_id": job_id,
        "user_id": user_id,
        "class_id": class_id,
        "s3_bucket": bucket,
        "s3_key": key,
    }
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body),
    )
    logger.info("Enqueued message to %s", queue_url)


def check_job_status(supabase, job_id: str) -> dict:
    """Get job status and summary fields."""
    result = (
        supabase.table("jobs")
        .select("status, error_message, present_count, unknown_count")
        .eq("id", job_id)
        .single()
        .execute()
    )
    return result.data or {}


def check_attendance_results(supabase, session_id: str) -> list:
    """Get attendance results for a session."""
    result = (
        supabase.table("attendance_results")
        .select("student_id, confidence, face_index")
        .eq("session_id", session_id)
        .execute()
    )
    return result.data or []


def cleanup(supabase, s3_client, job_id: str, session_id: str, bucket: str, key: str) -> None:
    """Clean up test data."""
    try:
        # Delete attendance results
        supabase.table("attendance_results").delete().eq("session_id", session_id).execute()
        logger.info("Deleted attendance results for session %s", session_id)
    except Exception as e:
        logger.warning("Failed to delete attendance results: %s", e)

    try:
        # Delete attendance session
        supabase.table("attendance_sessions").delete().eq("id", session_id).execute()
        logger.info("Deleted attendance session %s", session_id)
    except Exception as e:
        logger.warning("Failed to delete attendance session: %s", e)

    try:
        # Delete job
        supabase.table("jobs").delete().eq("id", job_id).execute()
        logger.info("Deleted job %s", job_id)
    except Exception as e:
        logger.warning("Failed to delete job: %s", e)

    try:
        # Delete S3 object
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info("Deleted s3://%s/%s", bucket, key)
    except Exception as e:
        logger.warning("Failed to delete S3 object: %s", e)


def run_smoke_test(args: argparse.Namespace) -> SmokeResult:
    """Run the attendance worker smoke test."""
    settings = get_settings()
    supabase = get_supabase_client()
    s3_client = get_s3_client()
    sqs_client = get_sqs_client()

    # Configuration
    bucket = args.bucket or settings.s3_attendance_bucket
    queue_url = settings.sqs_attendance_queue_url
    if not queue_url:
        return SmokeResult(False, "SQS_ATTENDANCE_QUEUE_URL not configured")

    # Generate test IDs
    run_id = str(uuid.uuid4())[:8]
    job_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    s3_key = f"attendance-photos/smoke-tests/{args.class_id}/{run_id}.jpg"

    logger.info("=" * 60)
    logger.info("Starting smoke test with:")
    logger.info("  Class ID: %s", args.class_id)
    logger.info("  Instructor ID: %s", args.instructor_id)
    logger.info("  Job ID: %s", job_id)
    logger.info("  Session ID: %s", session_id)
    logger.info("  S3 Key: %s", s3_key)
    logger.info("  Embedding Mode: %s", args.embedding_mode)
    logger.info("=" * 60)

    try:
        # Step 1: Upload test image
        upload_test_image(s3_client, bucket, s3_key, args.image_path)

        # Step 2: Create job
        create_attendance_job(supabase, job_id, args.instructor_id, bucket, s3_key)

        # Step 3: Create attendance session
        create_attendance_session(
            supabase, session_id, args.class_id, args.instructor_id, job_id
        )

        # Step 4: Enqueue message
        enqueue_attendance_message(
            sqs_client, queue_url, job_id, args.instructor_id, args.class_id, bucket, s3_key
        )

        # Step 5: Run worker (it will process our message)
        logger.info("Running attendance worker...")
        
        # Override settings for test
        import os
        os.environ["WORKER_EMBEDDING_MODE"] = args.embedding_mode
        os.environ["WORKER_MAX_EMPTY_POLLS"] = "3"

        worker = AttendanceWorker()
        worker.run()

        # Step 6: Verify results
        job_status = check_job_status(supabase, job_id)
        logger.info("Job status: %s", job_status)

        if job_status.get("status") != "SUCCEEDED":
            return SmokeResult(
                False,
                f"Job did not succeed: {job_status.get('error_message', 'unknown error')}"
            )

        results = check_attendance_results(supabase, session_id)
        logger.info("Attendance results: %d rows", len(results))
        for r in results:
            logger.info("  Face %d: student=%s, confidence=%.3f",
                r.get("face_index", -1),
                r.get("student_id", "UNKNOWN"),
                r.get("confidence") or 0.0
            )

        present = job_status.get("present_count", 0)
        unknown = job_status.get("unknown_count", 0)
        logger.info("Summary: %d present, %d unknown", present, unknown)

        return SmokeResult(
            True,
            f"Success! Processed {len(results)} faces: {present} present, {unknown} unknown"
        )

    except Exception as e:
        logger.exception("Smoke test failed")
        return SmokeResult(False, str(e))

    finally:
        # Cleanup
        logger.info("Cleaning up test data...")
        cleanup(supabase, s3_client, job_id, session_id, bucket, s3_key)


def main():
    args = parse_args()
    result = run_smoke_test(args)

    if result.passed:
        logger.info("✅ SMOKE TEST PASSED: %s", result.message)
        sys.exit(0)
    else:
        logger.error("❌ SMOKE TEST FAILED: %s", result.message)
        sys.exit(1)


if __name__ == "__main__":
    main()
