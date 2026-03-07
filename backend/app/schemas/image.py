from uuid import UUID

from pydantic import BaseModel


class UploadUrlResponse(BaseModel):
    upload_url: str
    bucket: str
    key: str
    job_id: UUID | None = None


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    error_message: str | None = None