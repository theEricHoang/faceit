"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient, PyJWTError

from app.db.supabase import get_supabase_client

from app.core.config import get_settings
from app.models.instructor import ProfileType
from app.schemas.user import CurrentUser

security = HTTPBearer()

# Cache the JWKS client
_jwks_client = None

def get_jwks_client():
    """Get cached JWKS client for Supabase."""
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client

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
    try:
        # Get the signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(credentials.credentials)
        
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        jwt_type = payload.get("user_metadata", {}).get("type")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        # Attempt to read the authoritative profile type from the database
        # so that we don't rely solely on JWT metadata (which may be stale).
        profile_type = ProfileType.STUDENT
        try:
            client = get_supabase_client()
            resp = (
                client
                .table("profiles")
                .select("type")
                .eq("id", str(user_id))
                .single()
                .execute()
            )
            profile_data = resp.data or {}
            if profile_data.get("type"):
                profile_type = ProfileType(profile_data.get("type"))
            elif jwt_type:
                # fallback to token if DB record missing type
                profile_type = ProfileType(jwt_type)
        except Exception:
            # ignore DB errors and fall back to JWT metadata or default
            if jwt_type:
                profile_type = ProfileType(jwt_type)

        return CurrentUser(
            user_id=UUID(user_id),
            email=email,
            type=profile_type,
        )

    except PyJWTError as e:
        print(f"DEBUG: JWTError occurred: {type(e).__name__}: {e}")
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
