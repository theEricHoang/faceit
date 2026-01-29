from fastapi import APIRouter, HTTPException, status

from app.schemas.user import InstructorSignupRequest, InstructorSignupResponse
from app.services.auth_service import AuthService, SignupError

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
