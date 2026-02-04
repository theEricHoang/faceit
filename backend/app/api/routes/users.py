from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.user import CurrentUser, UserProfileResponse, ChangePasswordRequest, ChangePasswordResponse
from app.services.user_profile_service import UserProfileService, UserProfileServiceError
from app.services.user_account_service import UserAccountService, UserAccountServiceError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
	current_user: CurrentUser = Depends(get_current_user),
):
	"""Return current user's profile info (name, student number, email)."""
	service = UserProfileService()
	try:
		profile = service.get_profile_names_and_type(current_user.user_id)
		student_number = service.get_student_number(current_user.user_id)

		full_name = f"{profile['first_name']} {profile['last_name']}"

		return UserProfileResponse(
			user_id=current_user.user_id,
			email=current_user.email,
			type=profile.get("type", current_user.type),
			first_name=profile["first_name"],
			last_name=profile["last_name"],
			full_name=full_name,
			student_id=student_number,
		)
	except UserProfileServiceError as e:
		raise HTTPException(status_code=404, detail=str(e))


@router.post("/me/change-password", response_model=ChangePasswordResponse)
async def change_my_password(
	payload: ChangePasswordRequest,
	current_user: CurrentUser = Depends(get_current_user),
):
	"""Change the current user's password.

	Requires authentication; uses Supabase Admin API to update password.
	"""
	service = UserAccountService()
	try:
		service.change_password(current_user.user_id, payload.new_password)
		return ChangePasswordResponse()
	except UserAccountServiceError as e:
		raise HTTPException(status_code=400, detail=str(e))

