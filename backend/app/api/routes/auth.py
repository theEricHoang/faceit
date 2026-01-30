from fastapi import APIRouter, HTTPException, status

from app.schemas.user import (
    InstructorSignupRequest,
    InstructorSignupResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.services.auth_service import (
    AuthService,
    LoginError,
    RefreshError,
    SignupError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup/instructor",
    response_model=InstructorSignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_instructor(
    request: InstructorSignupRequest,
) -> InstructorSignupResponse:
    """Sign up a new instructor.

    Creates an auth user, profile, and instructor record.
    """
    auth_service = AuthService()

    try:
        return await auth_service.signup_instructor(request)
    except SignupError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(request: LoginRequest) -> LoginResponse:
    """Log in a user with email and password.

    Returns access and refresh tokens along with user profile data.
    Works for both students and instructors.
    """
    auth_service = AuthService()

    try:
        return await auth_service.login(request)
    except LoginError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(request: RefreshRequest) -> RefreshResponse:
    """Refresh an access token using a refresh token.

    Returns new access and refresh tokens.
    """
    auth_service = AuthService()

    try:
        return await auth_service.refresh_token(request)
    except RefreshError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
