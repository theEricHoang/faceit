import argparse
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError, TokenRetrievalError
from postgrest.exceptions import APIError

from app.core.config import get_settings
from app.db.supabase import get_supabase_client
from app.worker.enrollment_worker import EnrollmentWorker

LOGGER = logging.getLogger(__name__)


@dataclass
class SmokeResult:
    passed: bool
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end smoke test for enrollment worker (v0 or v1)."
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="User UUID for embedding insert (face_embeddings.user_id).",
    )
    parser.add_argument(
        "--owner-user-id",
        default=None,
        help="Optional owner UUID for jobs.owner_user_id (defaults to --user-id).",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Optional S3 bucket override (defaults to S3_ENROLLMENT_BUCKET).",
    )
    parser.add_argument(
        "--embedding-mode",
        default="v0",
        choices=["v0", "v1"],
        help="Worker embedding mode to test (v0 uses stub embeddings, v1 uses InsightFace).",
    )
    parser.add_argument(
        "--skip-failure-path",
        action="store_true",
        help="Skip the bad-key failure path test.",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upload_dummy_image(s3_client: boto3.client, bucket: str, key: str) -> None:
    jpeg_like_content = b"\xff\xd8\xff\xe0SMOKE_TEST_FACEIT\xff\xd9"
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=jpeg_like_content,
        ContentType="image/jpeg",
    )


def create_job(
    supabase,
    job_id: str,
    owner_user_id: str,
    bucket: str,
    key: str,
) -> None:
    try:
        result = (
            supabase
            .table("jobs")
            .insert(
                {
                    "id": job_id,
                    "kind": "ENROLLMENT",
                    "status": "PENDING",
                    "owner_user_id": owner_user_id,
                    "s3_bucket": bucket,
                    "s3_key": key,
                }
            )
            .execute()
        )
    except APIError as exc:
        code = exc.json().get("code") if callable(getattr(exc, "json", None)) else None
        message = exc.json().get("message") if callable(getattr(exc, "json", None)) else str(exc)
        if code == "23503" and "jobs_owner_user_id_fkey" in str(message):
            raise RuntimeError(
                "Invalid owner_user_id for jobs FK. Use a real app user UUID (for example from profiles.id), "
                "or pass --owner-user-id separately."
            ) from exc
        raise

    if result.data is None:
        raise RuntimeError(f"Failed to create job {job_id}")


def send_job_message(sqs_client, queue_url: str, body: dict) -> None:
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))


def get_job(supabase, job_id: str) -> dict:
    result = (
        supabase
        .table("jobs")
        .select("id,status,error_message,updated_at")
        .eq("id", job_id)
        .single()
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"Job {job_id} not found")
    return result.data


def count_recent_embeddings(
    supabase,
    user_id: str,
    since_iso: str,
    model: str,
) -> int:
    result = (
        supabase
        .table("face_embeddings")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("model", model)
        .gte("created_at", since_iso)
        .execute()
    )
    return result.count or 0


def queue_depth(sqs_client, queue_url: str) -> dict[str, int]:
    response = sqs_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )
    attrs = response.get("Attributes", {})
    return {
        "visible": int(attrs.get("ApproximateNumberOfMessages", "0")),
        "inflight": int(attrs.get("ApproximateNumberOfMessagesNotVisible", "0")),
    }


def resolve_user_lookup_mode(supabase) -> str:
    try:
        (
            supabase
            .schema("auth")
            .table("users")
            .select("id")
            .limit(1)
            .execute()
        )
        return "auth"
    except APIError as exc:
        error = exc.json() if callable(getattr(exc, "json", None)) else {}
        code = error.get("code")
        if code == "PGRST106":
            LOGGER.warning(
                "auth schema is not exposed via PostgREST; using public.profiles for user existence checks"
            )
            return "profiles"
        raise RuntimeError(
            "Unable to determine user lookup mode from Supabase API."
        ) from exc


def assert_user_exists(supabase, user_id: str, label: str, lookup_mode: str) -> None:
    if lookup_mode == "auth":
        result = (
            supabase
            .schema("auth")
            .table("users")
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise RuntimeError(
                f"{label} '{user_id}' is not present in auth.users. Use a valid auth user UUID."
            )
        return

    if lookup_mode == "profiles":
        result = (
            supabase
            .table("profiles")
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise RuntimeError(
                f"{label} '{user_id}' not found in public.profiles (auth.users not accessible). Use a valid app user UUID."
            )
        return

    raise RuntimeError(f"Unknown user lookup mode: {lookup_mode}")


def run_smoke_test(
    user_id: str,
    owner_user_id: str | None,
    bucket_override: str | None,
    skip_failure_path: bool,
    embedding_mode: str,
) -> int:
    settings = get_settings()
    supabase = get_supabase_client()

    if settings.aws_profile:
        session = boto3.Session(profile_name=settings.aws_profile)
    else:
        session = boto3.Session()

    s3_client = session.client("s3", region_name=settings.aws_region)
    sqs_client = session.client("sqs", region_name=settings.aws_region)
    sts_client = session.client("sts", region_name=settings.aws_region)

    try:
        identity = sts_client.get_caller_identity()
        LOGGER.info("Using AWS account %s", identity.get("Account"))
    except TokenRetrievalError as exc:
        raise RuntimeError(
            "AWS SSO token expired. Run 'aws sso login --profile dev' (or your AWS_PROFILE), then rerun the smoke test."
        ) from exc

    bucket = bucket_override or settings.s3_enrollment_bucket
    queue_url = settings.sqs_enrollment_queue_url
    owner_id = owner_user_id or user_id

    lookup_mode = resolve_user_lookup_mode(supabase)
    assert_user_exists(supabase, owner_id, "owner_user_id", lookup_mode)
    assert_user_exists(supabase, user_id, "user_id", lookup_mode)

    run_id = str(uuid.uuid4())
    started_at = utc_now_iso()

    happy_job_id = str(uuid.uuid4())
    bad_job_id = str(uuid.uuid4())

    happy_key = f"enrollment-photos/smoke-tests/{user_id}/{run_id}.jpg"
    bad_key = f"enrollment-photos/smoke-tests/{user_id}/{run_id}-missing.jpg"

    LOGGER.info("Creating test object in S3: s3://%s/%s", bucket, happy_key)
    upload_dummy_image(s3_client, bucket, happy_key)

    LOGGER.info("Creating jobs in Supabase")
    create_job(supabase, happy_job_id, owner_id, bucket, happy_key)
    if not skip_failure_path:
        create_job(supabase, bad_job_id, owner_id, bucket, bad_key)

    LOGGER.info("Queue depth before enqueue: %s", queue_depth(sqs_client, queue_url))

    LOGGER.info("Enqueueing happy-path job")
    send_job_message(
        sqs_client,
        queue_url,
        {
            "job_id": happy_job_id,
            "user_id": user_id,
            "s3_bucket": bucket,
            "s3_key": happy_key,
        },
    )

    if not skip_failure_path:
        LOGGER.info("Enqueueing failure-path job")
        send_job_message(
            sqs_client,
            queue_url,
            {
                "job_id": bad_job_id,
                "user_id": user_id,
                "s3_bucket": bucket,
                "s3_key": bad_key,
            },
        )

    LOGGER.info("Running worker to drain queue (embedding_mode=%s)", embedding_mode)
    worker = EnrollmentWorker(client=supabase)
    worker.run()

    LOGGER.info("Queue depth after worker: %s", queue_depth(sqs_client, queue_url))

    results: list[SmokeResult] = []

    happy_job = get_job(supabase, happy_job_id)
    happy_status = str(happy_job.get("status") or "").lower()
    if happy_status == "succeeded":
        results.append(SmokeResult(True, "Happy path job marked succeeded"))
    else:
        results.append(
            SmokeResult(False, f"Happy path job status expected succeeded, got {happy_job.get('status')}")
        )

    model = "worker-v0" if embedding_mode == "v0" else "insightface-worker-v1"
    embeddings_count = count_recent_embeddings(supabase, user_id, started_at, model)
    if embeddings_count >= 1:
        results.append(
            SmokeResult(True, f"At least one embedding created since test start (count={embeddings_count})")
        )
    else:
        results.append(SmokeResult(False, "No embedding created by worker"))

    if not skip_failure_path:
        bad_job = get_job(supabase, bad_job_id)
        bad_status = bad_job.get("status")
        bad_status_normalized = str(bad_status or "").lower()
        bad_error = bad_job.get("error_message") or ""
        if bad_status_normalized == "failed":
            results.append(SmokeResult(True, "Failure path job marked failed"))
        else:
            results.append(
                SmokeResult(False, f"Failure path status expected failed, got {bad_status}")
            )

        if bad_error.startswith("WORKER_ERROR:"):
            results.append(SmokeResult(True, "Failure path stored error code prefix in error_message"))
        else:
            results.append(
                SmokeResult(False, f"Failure path error_message missing WORKER_ERROR prefix: {bad_error}")
            )

    print("\n=== Smoke Test Results ===")
    for item in results:
        marker = "PASS" if item.passed else "FAIL"
        print(f"[{marker}] {item.message}")

    print("\n=== Test Artifact IDs ===")
    print(f"happy_job_id={happy_job_id}")
    if not skip_failure_path:
        print(f"bad_job_id={bad_job_id}")
    print(f"happy_s3_key={happy_key}")

    failures = [item for item in results if not item.passed]
    return 1 if failures else 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    os.environ["WORKER_EMBEDDING_MODE"] = args.embedding_mode
    get_settings.cache_clear()

    try:
        exit_code = run_smoke_test(
            user_id=args.user_id,
            owner_user_id=args.owner_user_id,
            bucket_override=args.bucket,
            skip_failure_path=args.skip_failure_path,
            embedding_mode=args.embedding_mode,
        )
    except (BotoCoreError, ClientError, RuntimeError, ValueError, TokenRetrievalError) as exc:
        LOGGER.exception("Smoke test failed with error: %s", exc)
        raise SystemExit(1)

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
