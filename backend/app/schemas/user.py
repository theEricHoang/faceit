from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.instructor import ProfileType


class InstructorSignupRequest(BaseModel):
    """Request schema for instructor signup."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    department: str | None = Field(default=None, max_length=100)
    office_location: str | None = Field(default=None, max_length=200)


class InstructorSignupResponse(BaseModel):
    """Response schema for successful instructor signup."""

    user_id: UUID
    email: str
    first_name: str
    last_name: str
    bio: str | None
    type: ProfileType
    department: str | None
    office_location: str | None
