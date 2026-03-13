
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.course import CreateClassRequest, CreateClassResponse, ListClassesResponse, ClassListItem, JoinClassRequest, JoinClassResponse, ClassDetailResponse, WithdrawClassResponse
from app.schemas.image import UploadUrlResponse
from app.schemas.user import CurrentUser
from app.services.classes.class_query_service import ClassService as ClassQueryService
from app.services.classes.class_service import ClassService, CreateClassError
from app.services.enrollment_service import EnrollmentService, EnrollmentServiceError
from app.services.storage_service import StorageService
from app.services.job_service import JobService, CreateJobError
from app.services.attendance_service import AttendanceService, CreateSessionError
from app.api.deps import (
    get_current_user,
    get_attendance_service,
    get_job_service,
    get_query_service,
    get_storage_service,
    require_instructor,
)

router = APIRouter(prefix="/classes", tags=["classes"])

def get_class_service():
    return ClassService()

def get_enrollment_service():
    return EnrollmentService()

@router.get("", response_model=ListClassesResponse)
async def list_classes(
    current_user: CurrentUser = Depends(get_current_user),
    query_service: ClassQueryService = Depends(get_query_service),
):
    """List classes for the current user (instructor or student)."""
    try:
        classes = query_service.get_classes_for_user(current_user.user_id, current_user.type.value)
        return ListClassesResponse(
            classes=[
                ClassListItem(
                    class_id=UUID(str(cls.get("id"))),
                    course_code=cls.get("course_code"),
                    course_name=cls.get("course_name"),
                    section=cls.get("section"),
                    term=cls.get("term"),
                    schedule=cls.get("schedule"),
                    room=cls.get("room"),
                )
                for cls in classes
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/open", response_model=ListClassesResponse)
async def list_open_classes(
    query_service: ClassQueryService = Depends(get_query_service),
):
    """List all classes available in the system (Open Classes)."""
    try:
        classes = query_service.get_all_classes()
        return ListClassesResponse(
            classes=[
                ClassListItem(
                    class_id=UUID(str(cls.get("id"))),
                    course_code=cls.get("course_code"),
                    course_name=cls.get("course_name"),
                    section=cls.get("section"),
                    term=cls.get("term"),
                    schedule=cls.get("schedule"),
                    room=cls.get("room"),
                )
                for cls in (classes or [])
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{class_id}", response_model=ClassDetailResponse)
async def get_class_details(
    class_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    query_service: ClassQueryService = Depends(get_query_service),
):
    """Get class details including instructor name. Available to authenticated users."""
    try:
        cls = query_service.get_class_details(class_id)
        return ClassDetailResponse(
            class_id=UUID(str(cls.get("id"))),
            course_code=cls.get("course_code"),
            course_name=cls.get("course_name"),
            section=cls.get("section"),
            schedule=cls.get("schedule"),
            room=cls.get("room"),
            instructor_name=cls.get("instructor_name") or "",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("", response_model=CreateClassResponse)
async def create_class(
    payload: CreateClassRequest,
    current_user: CurrentUser = Depends(get_current_user),
    class_service: ClassService = Depends(get_class_service),
):
    """Create a new class. Only instructors can create classes."""
    if current_user.type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can create classes")
    
    try:
        result = await class_service.create_class(
            instructor_id=current_user.user_id,
            course_code=payload.course_code,
            course_name=payload.course_name,
            section=payload.section,
            term=payload.term,
            schedule=payload.schedule,
            room=payload.room,
        )
        return CreateClassResponse(
            class_id=UUID(result["id"]),
            course_code=result["course_code"],
            course_name=result["course_name"],
            section=result["section"],
            term=result["term"],
        )
    except CreateClassError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/join", response_model=JoinClassResponse)
async def join_class_by_code(
    payload: JoinClassRequest,
    current_user: CurrentUser = Depends(get_current_user),
    enroll_service: EnrollmentService = Depends(get_enrollment_service),
):
    """Join a class by section. Students only."""
    if current_user.type != "student":
        raise HTTPException(status_code=403, detail="Only students can join classes")
    try:
        result = enroll_service.join_by_section(current_user.user_id, payload.section)
        return JoinClassResponse(
            class_id=UUID(str(result["class_id"])),
            student_id=current_user.user_id,
            course_name=result.get("course_name"),
            section=result.get("section"),
        )
    except EnrollmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{class_id}/attendance/upload-url", response_model=UploadUrlResponse, status_code=status.HTTP_200_OK)
async def get_attendance_upload_url(
    class_id: UUID,
    session_id: UUID | None = None,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    storage_service: StorageService = Depends(get_storage_service),
    job_service: JobService = Depends(get_job_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> UploadUrlResponse:
    """Generate a pre-signed URL for uploading a class attendance photo.

    Creates a batch session on the first request, then returns upload URLs
    for additional photos within the same session when session_id is provided.
    """
    has_access = query_service.instructor_has_class(current_user.user_id, class_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Class not found")

    if session_id is None:
        session_id = uuid4()
        job_id = uuid4()
        result = storage_service.generate_attendance_presigned_upload_url(
            class_id=str(class_id),
            instructor_id=str(current_user.user_id),
            session_id=str(session_id),
        )

        try:
            job_service.create_pending_attendance_job(
                job_id=str(job_id),
                user_id=str(current_user.user_id),
                bucket=result["bucket"],
                key=result["key_prefix"],
            )
        except CreateJobError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

        try:
            session_row = attendance_service.create_session(
                class_id=class_id,
                instructor_id=current_user.user_id,
                job_id=job_id,
                session_id=session_id,
            )
        except CreateSessionError as e:
            job_service.rollback_job(str(job_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
    else:
        try:
            session_row = attendance_service.get_session(session_id, class_id)
        except SessionNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        job_id = UUID(str(session_row["job_id"]))
        result = storage_service.generate_attendance_presigned_upload_url(
            class_id=str(class_id),
            instructor_id=str(current_user.user_id),
            session_id=str(session_id),
        )

    return UploadUrlResponse(
        upload_url=result["upload_url"],
        bucket=result["bucket"],
        key=result["key"],
        job_id=job_id,
        session_id=session_row["id"],
    )

@router.delete("/{class_id}/withdraw", response_model=WithdrawClassResponse)
async def withdraw_from_class(
    class_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    enroll_service: EnrollmentService = Depends(get_enrollment_service),
):
    """Withdraw student from a class (remove enrollment). Students only."""
    if current_user.type != "student":
        raise HTTPException(status_code=403, detail="Only students can withdraw from classes")
    try:
        result = enroll_service.withdraw_from_class(current_user.user_id, class_id)
        return WithdrawClassResponse(class_id=UUID(str(result["class_id"])), student_id=current_user.user_id)
    except EnrollmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))