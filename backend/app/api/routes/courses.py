
from fastapi import APIRouter, Depends, Header, HTTPException
from uuid import UUID
from app.schemas.course import CreateClassRequest, CreateClassResponse, ListClassesResponse, ClassListItem
from app.schemas.user import CurrentUser
from app.services.classes.class_query_service import ClassService as ClassQueryService
from app.services.classes.class_service import ClassService, CreateClassError
from app.api.deps import get_current_user

router = APIRouter(prefix="/classes", tags=["classes"])
query_service = ClassQueryService()
class_service = ClassService()

@router.get("", response_model=ListClassesResponse)
async def list_classes(
    x_user_id: str = Header(..., description="Mock user id header"),
    x_user_type: str = Header(..., description="Mock user type header (instructor or student)"),
):
    """List classes for the current user (instructor or student)."""
    try:
        user_id = UUID(x_user_id)
        user_type = x_user_type.lower()
        classes = query_service.get_classes_for_user(user_id, user_type)
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