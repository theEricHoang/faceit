from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.job import JobKind, JobStatus


class CreateJobRequest(BaseModel):
    kind: Literal["ENROLLMENT"] = Field(
        ..., description="Job type. Currently only ENROLLMENT is supported."
    )
    bucket: str = Field(..., min_length=1, description="S3 bucket where the image was uploaded.")
    key: str = Field(..., min_length=1, description="S3 object key for the uploaded image.")


class CreateJobResponse(BaseModel):
    job_id: UUID


class JobStatusResponse(BaseModel):
    """Response schema for job status queries."""

    job_id: UUID
    status: JobStatus
    kind: JobKind
    error_message: str | None = None
    updated_at: datetime
