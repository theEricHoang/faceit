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

class JoinClassRequest(BaseModel):
    section: str

class JoinClassResponse(BaseModel):
    class_id: UUID
    student_id: UUID
    course_name: str
    section: str

class ClassDetailResponse(BaseModel):
    class_id: UUID
    course_code: str
    course_name: str
    section: str
    schedule: str
    room: Optional[str]
    instructor_name: str

class WithdrawClassResponse(BaseModel):
    class_id: UUID
    student_id: UUID


class EnrolledStudentItem(BaseModel):
    student_id: UUID
    first_name: str
    last_name: str
    email: str


class ClassEnrolledStudentsResponse(BaseModel):
    class_id: UUID
    students: List[EnrolledStudentItem]
