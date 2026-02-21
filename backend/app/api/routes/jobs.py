from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_student
from app.schemas.job import CreateJobRequest, CreateJobResponse
from app.schemas.user import CurrentUser
from app.services.job_service import JobService, CreateJobError

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
