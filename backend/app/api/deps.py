"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Validate JWT token and return current user.

    Decodes the Supabase JWT and extracts user information.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        CurrentUser with user_id, email, and type.

    Raises:
        HTTPException: 401 if token is invalid, expired, or malformed.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        user_type = payload.get("user_metadata", {}).get("type")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        # If type not in JWT metadata, default to student
        # In production, you might want to fetch from DB instead
        profile_type = ProfileType(user_type) if user_type else ProfileType.STUDENT

        return CurrentUser(
            user_id=UUID(user_id),
            email=email,
            type=profile_type,
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def require_instructor(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require the current user to be an instructor.

    Args:
        current_user: The authenticated user from get_current_user.

    Returns:
        CurrentUser if user is an instructor.

    Raises:
        HTTPException: 403 if user is not an instructor.
    """
    if current_user.type != ProfileType.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required",
        )
    return current_user


async def require_student(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require the current user to be a student.

    Args:
        current_user: The authenticated user from get_current_user.

    Returns:
        CurrentUser if user is a student.

    Raises:
        HTTPException: 403 if user is not a student.
    """
    if current_user.type != ProfileType.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user
