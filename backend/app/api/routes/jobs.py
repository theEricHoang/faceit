from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_student
from app.schemas.job import CreateJobRequest, CreateJobResponse, JobStatusResponse
from app.schemas.user import CurrentUser
from app.services.job_service import JobService, CreateJobError, JobNotFoundError

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateJobRequest,
    current_user: CurrentUser = Depends(require_student),
) -> CreateJobResponse:
    """Create an async processing job after uploading an image to S3."""
    service = JobService()
    try:
        return await service.create_enrollment_job(request, str(current_user.user_id))
    except CreateJobError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    current_user: CurrentUser = Depends(require_student),
) -> JobStatusResponse:
    """Get the current status of a job.

    Returns the job's status, kind, and error message (if failed).
    Students can only access their own jobs.
    """
    service = JobService()
    try:
        return await service.get_job_status(job_id, current_user.user_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
