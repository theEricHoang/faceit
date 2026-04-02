"""Routes for attendance session reports and job processing."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_attendance_service,
    get_job_service,
    get_query_service,
    require_instructor,
)
from app.schemas.attendance import AttendanceSessionResponse, CreateAttendanceJobResponse
from app.schemas.job import JobStatusResponse
from app.schemas.user import CurrentUser
from app.services.attendance_service import (
    AttendanceService,
    SessionNotFoundError,
)
from app.services.classes.class_query_service import ClassService as ClassQueryService
from app.services.job_service import (
    CreateJobError,
    JobNotFoundError,
    JobNotPendingError,
    JobOwnershipError,
    JobService,
)

router = APIRouter(prefix="/classes", tags=["attendance"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{class_id}/attendance/process/{job_id}",
    response_model=CreateAttendanceJobResponse,
    status_code=status.HTTP_200_OK,
)
async def process_attendance_job(
    class_id: UUID,
    job_id: UUID,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
    job_service: JobService = Depends(get_job_service),
) -> CreateAttendanceJobResponse:
    """Enqueue a PENDING attendance job for async processing.

    The instructor must own the class. The job must exist and be in
    PENDING status.
    """
    if not query_service.instructor_has_class(current_user.user_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    # Look up the session linked to this job
    try:
        session_id = attendance_service.get_session_id_for_job(job_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance session found for this job",
        )

    # Ensure the job's session belongs to the requested class_id.
    try:
        attendance_service.get_session(UUID(session_id), class_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance session found for this class and job",
        )

    try:
        return job_service.enqueue_attendance_job(
            job_id=str(job_id),
            user_id=str(current_user.user_id),
            class_id=str(class_id),
            session_id=str(session_id),
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (JobNotPendingError, JobOwnershipError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except CreateJobError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{class_id}/attendance/sessions/{session_id}/process",
    response_model=CreateAttendanceJobResponse,
    status_code=status.HTTP_200_OK,
)
async def process_attendance_session(
    class_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
    job_service: JobService = Depends(get_job_service),
) -> CreateAttendanceJobResponse:
    """Enqueue processing for a multi-image attendance session."""
    if not query_service.instructor_has_class(current_user.user_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    try:
        session = attendance_service.get_session(session_id, class_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    try:
        return job_service.enqueue_attendance_job(
            job_id=str(session["job_id"]),
            user_id=str(current_user.user_id),
            class_id=str(class_id),
            session_id=str(session_id),
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (JobNotPendingError, JobOwnershipError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except CreateJobError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{class_id}/attendance/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_attendance_job_status(
    class_id: UUID,
    job_id: UUID,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Poll the status of an attendance processing job.

    The instructor must own the class.
    """
    if not query_service.instructor_has_class(current_user.user_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    try:
        return await job_service.get_job_status(job_id, current_user.user_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )


@router.get(
    "/{class_id}/attendance/sessions/{session_id}",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_attendance_session_report(
    class_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceSessionResponse:
    """Return a display-ready attendance report for a single session.

    Access control: the requesting instructor must own the class.
    Returns 404 (not 403) to avoid leaking class existence.
    """
    if not query_service.instructor_has_class(current_user.user_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    try:
        report = attendance_service.get_session_report(session_id, class_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return AttendanceSessionResponse(**report)
