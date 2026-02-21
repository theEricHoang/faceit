from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    kind: Literal["ENROLLMENT"] = Field(
        ..., description="Job type. Currently only ENROLLMENT is supported."
    )
    bucket: str = Field(..., min_length=1, description="S3 bucket where the image was uploaded.")
    key: str = Field(..., min_length=1, description="S3 object key for the uploaded image.")


class CreateJobResponse(BaseModel):
    job_id: UUID
