from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ProfileType(str, Enum):
    """User profile type enum matching database constraint."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"


class Profile(BaseModel):
    """Data model representing the profiles table."""

    id: UUID
    first_name: str
    last_name: str
    bio: str | None = None
    type: ProfileType


class Instructor(BaseModel):
    """Data model representing the instructors table."""

    id: UUID
    department: str | None = None
    office_location: str | None = None
