from uuid import UUID
from supabase import Client

from app.db.supabase import get_supabase_client


class UserAccountServiceError(Exception):
    pass


class UserAccountService:
    """Service for account-related operations (like password changes)."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def change_password(self, user_id: UUID, new_password: str) -> None:
        """Change the user's password using Supabase Admin API.

        Args:
            user_id: The user's UUID.
            new_password: The new password to set.

        Raises:
            UserAccountServiceError: On failure to update password.
        """
        try:
            # Supabase Admin API: update user password by id
            self.client.auth.admin.update_user_by_id(
                str(user_id),
                {"password": new_password},
            )
        except Exception as e:
            raise UserAccountServiceError(f"Failed to change password: {e}")
