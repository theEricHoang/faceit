from uuid import UUID

from supabase import Client

from app.db.supabase import get_supabase_client
from app.models.instructor import ProfileType
from app.schemas.user import (
    InstructorSignupRequest,
    InstructorSignupResponse,
    LoginRequest,
    LoginResponse,
    LoginProfileData,
    RefreshRequest,
    RefreshResponse,
)


class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    pass


class SignupError(AuthServiceError):
    """Exception raised when signup fails."""

    pass


class LoginError(AuthServiceError):
    """Exception raised when login fails."""

    pass


class RefreshError(AuthServiceError):
    """Exception raised when token refresh fails."""

    pass


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    async def signup_instructor(
        self, request: InstructorSignupRequest
    ) -> InstructorSignupResponse:
        """Sign up a new instructor.

        Creates an auth user, then inserts profile and instructor records.
        If any step fails after auth user creation, the auth user is deleted
        to maintain consistency.

        Args:
            request: The instructor signup request data.

        Returns:
            InstructorSignupResponse with the created user data.

        Raises:
            SignupError: If signup fails at any step.
        """
        user_id: UUID | None = None

        try:
            # Step 1: Create auth user via Supabase Auth
            auth_response = self.client.auth.sign_up(
                {"email": request.email, "password": request.password}
            )

            if not auth_response.user:
                raise SignupError("Failed to create auth user")

            user_id = UUID(auth_response.user.id)

            if not auth_response.session:
                raise SignupError("Failed to create auth session")

            # Step 2: Insert profile record
            profile_data = {
                "id": str(user_id),
                "first_name": request.first_name,
                "last_name": request.last_name,
                "bio": request.bio,
                "type": ProfileType.INSTRUCTOR.value,
            }

            profile_result = self.client.table("profiles").insert(profile_data).execute()

            if not profile_result.data:
                raise SignupError("Failed to create profile record")

            # Step 3: Insert instructor record
            instructor_data = {
                "id": str(user_id),
                "department": request.department,
                "office_location": request.office_location,
            }

            instructor_result = (
                self.client.table("instructors").insert(instructor_data).execute()
            )

            if not instructor_result.data:
                raise SignupError("Failed to create instructor record")

            # Return successful response with auth tokens
            return InstructorSignupResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
                user_id=user_id,
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                bio=request.bio,
                type=ProfileType.INSTRUCTOR,
                department=request.department,
                office_location=request.office_location,
            )

        except SignupError:
            # Re-raise SignupError after cleanup
            if user_id:
                await self._delete_auth_user(user_id)
            raise

        except Exception as e:
            # Clean up auth user if it was created
            if user_id:
                await self._delete_auth_user(user_id)
            raise SignupError(f"Signup failed: {str(e)}") from e

    async def _delete_auth_user(self, user_id: UUID) -> None:
        """Delete an auth user for rollback purposes.

        Args:
            user_id: The UUID of the user to delete.
        """
        try:
            self.client.auth.admin.delete_user(str(user_id))
        except Exception:
            # Log error but don't raise - this is cleanup code
            # In production, you'd want proper logging here
            pass

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Log in a user with email and password.

        Authenticates via Supabase Auth and fetches the user's profile.

        Args:
            request: The login request with email and password.

        Returns:
            LoginResponse with tokens and user profile data.

        Raises:
            LoginError: If login fails or user has no profile.
        """
        try:
            # Authenticate with Supabase Auth
            auth_response = self.client.auth.sign_in_with_password(
                {"email": request.email, "password": request.password}
            )

            if not auth_response.user or not auth_response.session:
                raise LoginError("Invalid email or password")

            user_id = UUID(auth_response.user.id)

            # Fetch user profile
            profile_result = (
                self.client.table("profiles")
                .select("first_name, last_name, type")
                .eq("id", str(user_id))
                .single()
                .execute()
            )

            if not profile_result.data:
                raise LoginError("User profile not found")

            profile = LoginProfileData.model_validate(profile_result.data)

            return LoginResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
                user_id=user_id,
                email=auth_response.user.email or request.email,
                first_name=profile.first_name,
                last_name=profile.last_name,
                type=profile.type,
            )

        except LoginError:
            raise
        except Exception as e:
            raise LoginError(f"Login failed: {str(e)}") from e

    async def refresh_token(self, request: RefreshRequest) -> RefreshResponse:
        """Refresh an access token using a refresh token.

        Args:
            request: The refresh request with the refresh token.

        Returns:
            RefreshResponse with new access and refresh tokens.

        Raises:
            RefreshError: If token refresh fails.
        """
        try:
            auth_response = self.client.auth.refresh_session(request.refresh_token)

            if not auth_response.session:
                raise RefreshError("Failed to refresh token")

            return RefreshResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
            )

        except RefreshError:
            raise
        except Exception as e:
            raise RefreshError(f"Token refresh failed: {str(e)}") from e
