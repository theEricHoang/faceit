
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.schemas.course import CreateClassRequest, CreateClassResponse, ListClassesResponse, ClassListItem, JoinClassRequest, JoinClassResponse
from app.schemas.user import CurrentUser
from app.services.classes.class_query_service import ClassService as ClassQueryService
from app.services.classes.class_service import ClassService, CreateClassError
from app.services.enrollment_service import EnrollmentService, EnrollmentServiceError
from app.api.deps import get_current_user

router = APIRouter(prefix="/classes", tags=["classes"])
def get_query_service():
    return ClassQueryService()

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
    """Join a class by course_code. Students only."""
    if current_user.type != "student":
        raise HTTPException(status_code=403, detail="Only students can join classes")
    try:
        result = enroll_service.join_by_course_code(current_user.user_id, payload.course_code)
        return JoinClassResponse(
            class_id=UUID(str(result["class_id"])),
            student_id=current_user.user_id,
            course_name=result.get("course_name"),
            section=result.get("section"),
        )
    except EnrollmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))