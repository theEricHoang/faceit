import boto3
from botocore.config import Config
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def _get_boto3_session() -> boto3.Session:
    """Create a cached boto3 session.

    Uses the configured AWS profile if set, otherwise falls back to the
    default credential chain (env vars, instance profile, etc.).
    """
    settings = get_settings()
    if settings.aws_profile:
        return boto3.Session(profile_name=settings.aws_profile)
    return boto3.Session()


def get_sqs_client():
    """Get an SQS client.

    Uses a module-level cached session to avoid repeatedly loading
    AWS credentials and config on every request.
    """
    settings = get_settings()
    session = _get_boto3_session()
    return session.client(
        "sqs",
        region_name=settings.aws_region,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def get_s3_client():
    """Get an S3 client.

    Uses a module-level cached session to avoid repeatedly loading
    AWS credentials and config on every request.
    """
    settings = get_settings()
    session = _get_boto3_session()
    return session.client(
        "s3",
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )


def get_sts_client():
    """Get an STS client.

    Uses a module-level cached session to avoid repeatedly loading
    AWS credentials and config on every request.
    """
    settings = get_settings()
    session = _get_boto3_session()
    return session.client(
        "sts",
        region_name=settings.aws_region,
    )
