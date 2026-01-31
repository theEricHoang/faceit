
from fastapi import APIRouter, Header, HTTPException
from uuid import uuid4, UUID
from app.schemas.course import CreateClassRequest, CreateClassResponse, ListClassesResponse, ClassListItem
from app.services.classes.class_query_service import ClassService
import asyncio

router = APIRouter(prefix="/classes", tags=["classes"])
service = ClassService()

@router.get("", response_model=ListClassesResponse)
async def list_classes(
    x_user_id: str = Header(..., description="Mock user id header"),
    x_user_type: str = Header(..., description="Mock user type header (instructor or student)"),
):
    """List classes for the current user (instructor or student)."""
    try:
        user_id = UUID(x_user_id)
        user_type = x_user_type.lower()
        classes = service.get_classes_for_user(user_id, user_type)
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
def create_class(payload: CreateClassRequest):
    # TODO: connect to supabase
    return CreateClassResponse(
        class_id=uuid4(),
        course_code=payload.course_code,
        course_name=payload.course_name,
        section=payload.section,
        term=payload.term
    )