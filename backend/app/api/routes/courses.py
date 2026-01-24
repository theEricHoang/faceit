from fastapi import APIRouter
from uuid import uuid4
from app.schemas.course import CreateClassRequest, CreateClassResponse

router = APIRouter(prefix="/classes", tags=["classes"])

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