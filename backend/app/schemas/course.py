from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class CreateClassRequest(BaseModel):
    course_code: str
    section: str
    term: str
    schedule: str
    room: Optional[str]

class CreateClassResponse(BaseModel):
    class_id: UUID
    course_code: str
    section: str
    term: str
