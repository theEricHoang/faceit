from fastapi import APIRouter, Depends, status, HTTPException
from uuid import UUID

from app.api.deps import require_student
from app.schemas.image import UploadUrlResponse
from app.schemas.job import CreateJobResponse, JobStatusResponse
from app.schemas.user import CurrentUser
from app.services.storage_service import StorageService
from app.services.job_service import JobService, CreateJobError, JobNotFoundError

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("/upload-url", response_model=UploadUrlResponse, status_code=status.HTTP_200_OK)
async def get_enrollment_upload_url(
    current_user: CurrentUser = Depends(require_student),
) -> UploadUrlResponse:
    """Generate a pre-signed URL for uploading an enrollment photo.
    
    This endpoint creates a PENDING enrollment job and returns a pre-signed S3 URL
    for uploading the photo. The job_id is included in the S3 key to ensure uniqueness.
    
    After uploading to S3, the client should call POST /enrollments/{job_id}/process
    to finalize the job and enqueue it for processing.
    
    Returns:
        - upload_url: Pre-signed S3 URL for uploading the photo (1 hour expiry)
        - job_id: The enrollment job ID for subsequent API calls
        - bucket: S3 bucket name
        - key: S3 object key where the photo will be uploaded
    """
    job_service = JobService()
    storage_service = StorageService()
    
    try:
        import uuid
        job_id = uuid.uuid4()
        
        # Generate presigned URL first to get bucket and key
        url_result = storage_service.generate_presigned_upload_url(
            user_id=str(current_user.user_id),
            job_id=str(job_id),
        )
        
        # Create a PENDING job with the bucket and key information
        job_service.create_pending_enrollment_job(
            job_id=str(job_id),
            user_id=str(current_user.user_id),
            bucket=url_result["bucket"],
            key=url_result["key"],
        )
        
        return UploadUrlResponse(
            upload_url=url_result["upload_url"],
            bucket=url_result["bucket"],
            key=url_result["key"],
            job_id=job_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}",
        )


@router.post(
    "/{job_id}/process",
    response_model=CreateJobResponse,
    status_code=status.HTTP_200_OK,
)
async def process_enrollment_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(require_student),
) -> CreateJobResponse:
    """Finalize an enrollment job and enqueue it for processing.
    
    This endpoint should be called after the photo has been successfully uploaded
    to the pre-signed S3 URL. It will enqueue an SQS message to trigger the async
    worker that extracts face embeddings.
    
    Args:
        job_id: The enrollment job ID from the upload-url endpoint
    
    Returns:
        - job_id: The enrollment job ID
    
    Raises:
        404: Job not found or doesn't belong to the current user
        400: Job is not in PENDING status
        500: Failed to enqueue the job
    """
    job_service = JobService()
    
    try:
        response = await job_service.enqueue_enrollment_job(
            str(job_id), str(current_user.user_id)
        )
        return response
    except CreateJobError as e:
        # Determine correct status code based on error message
        error_msg = str(e)
        if "not found" in error_msg.lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "pending" in error_msg.lower() or "belong" in error_msg.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        raise HTTPException(status_code=status_code, detail=error_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process job: {str(e)}",
        )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_enrollment_job_status(
    job_id: UUID,
    current_user: CurrentUser = Depends(require_student),
) -> JobStatusResponse:
    """Get the status of an enrollment job.
    
    Clients can poll this endpoint to check if the embedding extraction is complete.
    
    Args:
        job_id: The enrollment job ID
    
    Returns:
        - job_id: The enrollment job ID
        - status: Current status (PENDING, RUNNING, SUCCEEDED, FAILED)
        - error_message: Error details if status is FAILED, otherwise None
    
    Raises:
        404: Job not found or doesn't belong to the current user
    """
    job_service = JobService()
    
    try:
        job = job_service.get_enrollment_job_status(
            str(job_id), str(current_user.user_id)
        )
        return JobStatusResponse(
            job_id=UUID(job["id"]),
            status=job["status"],
            kind=job["kind"],
            error_message=job.get("error_message"),
            updated_at=job["updated_at"],
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment job not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}",
        )