from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class JobStatus(str, Enum):
    """Job status enum matching database constraint."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobKind(str, Enum):
    """Job kind enum matching database constraint."""

    ENROLLMENT = "ENROLLMENT"
    ATTENDANCE = "ATTENDANCE"


class Job(BaseModel):
    """Data model representing the jobs table."""

    id: UUID
    kind: JobKind
    status: JobStatus
    owner_user_id: UUID
    s3_bucket: str
    s3_key: str
    error_message: str | None = None
    updated_at: datetime
