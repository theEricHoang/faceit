from uuid import UUID
from supabase import Client

from app.db.supabase import get_supabase_client
from app.models.instructor import ProfileType


class UserProfileServiceError(Exception):
    pass


class UserProfileService:
    """Service to read user profile-related data from Supabase."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def get_profile_names_and_type(self, user_id: UUID) -> dict:
        """Fetch first_name, last_name, and type from profiles table."""
        try:
            result = (
                self.client
                .table("profiles")
                .select("first_name, last_name, type")
                .eq("id", str(user_id))
                .single()
                .execute()
            )
            if not result.data:
                raise UserProfileServiceError("Profile not found")
            return result.data
        except Exception as e:
            raise UserProfileServiceError(f"Failed to fetch profile: {e}")

    def get_student_number(self, user_id: UUID) -> str | None:
        """Fetch student number from students table if present."""
        try:
            result = (
                self.client
                .table("students")
                .select("number")
                .eq("id", str(user_id))
                .single()
                .execute()
            )
            if result.data and "number" in result.data and result.data["number"]:
                return str(result.data["number"])
            return None
        except Exception:
            # If not a student or no record, return None without failing the request
            return None
