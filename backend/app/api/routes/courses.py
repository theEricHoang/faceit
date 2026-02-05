
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.schemas.course import CreateClassRequest, CreateClassResponse, ListClassesResponse, ClassListItem
from app.schemas.student import ClassEnrolledStudentsResponse, StudentEnrollmentItem
from app.schemas.user import CurrentUser
from app.services.classes.class_query_service import ClassService as ClassQueryService
from app.services.classes.class_service import ClassService, CreateClassError
from app.services.classes.class_read_repository import ClassReadRepository, ClassReadError
from app.api.deps import get_current_user

router = APIRouter(prefix="/classes", tags=["classes"])
def get_query_service():
    return ClassQueryService()

def get_class_service():
    return ClassService()

def get_read_repository():
    return ClassReadRepository()

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

@router.get("/{class_id}/students", response_model=ClassEnrolledStudentsResponse)
async def get_class_students(
    class_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    read_repo: ClassReadRepository = Depends(get_read_repository),
):
    """Get all students enrolled in a class. Only the instructor of the class can view this."""
    if current_user.type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can view enrolled students")
    
    try:
        # Verify the instructor owns this class
        classes = read_repo.get_classes_by_instructor(current_user.user_id)
        if not any(cls.get("id") == str(class_id) for cls in classes):
            raise HTTPException(status_code=403, detail="You do not have permission to view this class's students")
        
        students = read_repo.get_students_by_class(class_id)
        return ClassEnrolledStudentsResponse(
            class_id=class_id,
            students=[
                StudentEnrollmentItem(
                    user_id=UUID(str(student.get("id"))),
                    first_name=student.get("first_name"),
                    last_name=student.get("last_name"),
                    email=student.get("email"),
                )
                for student in students
            ]
        )
    except ClassReadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))