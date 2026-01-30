from typing import Optional
from uuid import UUID

from supabase import Client
from app.db.supabase import get_supabase_client

class ClassServiceError(Exception):
    """Base exception for class service errors."""
    pass

class CreateClassError(ClassServiceError):
    """Exception raised when class creation fails."""
    pass

class ClassService:
    """Service for handling class/course operations."""
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    async def create_class(
        self,
        instructor_id: UUID,
        course_code: str,
        course_name: str,
        section: str,
        term: str,
        schedule: str,
        room: Optional[str] = None,
    ) -> dict:
        """Create a new class/course record in Supabase."""
        class_data = {
            "instructor_id": str(instructor_id),
            "course_code": course_code,
            "course_name": course_name,
            "section": section,
            "term": term,
            "schedule": schedule,
            "room": room,
        }
        try:
            result = self.client.table("classes").insert(class_data).execute()
            if not result.data:
                raise CreateClassError("Failed to create class record")
            return result.data[0]
        except Exception as e:
            raise CreateClassError(f"Class creation failed: {str(e)}") from e
