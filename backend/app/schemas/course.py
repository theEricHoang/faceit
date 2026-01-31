from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class ClassListItem(BaseModel):
    class_id: UUID
    course_code: str
    course_name: str
    section: str
    term: str
    schedule: str
    room: Optional[str]

class ListClassesResponse(BaseModel):
    classes: List[ClassListItem]

class CreateClassRequest(BaseModel):
    course_code: str
    course_name: str
    section: str
    term: str
    schedule: str
    room: Optional[str] = None

class CreateClassResponse(BaseModel):
    class_id: UUID
    course_code: str
    course_name: str
    section: str
    term: str
