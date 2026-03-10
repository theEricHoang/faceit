from uuid import UUID
from pydantic import BaseModel, EmailStr


class StudentEnrollmentItem(BaseModel):
    """Student info in enrollment list."""
    user_id: UUID
    first_name: str
    last_name: str
    email: EmailStr | None = None


class ClassEnrolledStudentsResponse(BaseModel):
    """Response with list of students enrolled in a class."""
    class_id: UUID
    students: list[StudentEnrollmentItem]
