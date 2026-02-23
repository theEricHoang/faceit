from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.image import UploadUrlResponse
from app.schemas.user import CurrentUser
from app.services.storage_service import StorageService

router = APIRouter(prefix="/enrollment", tags=["enrollment"])

@router.post("/photos/upload-url", response_model=UploadUrlResponse)
async def get_photo_upload_url(
    current_user: CurrentUser = Depends(get_current_user),
) -> UploadUrlResponse:
    """Generate a pre-signed URL for uploading an enrollment photo."""
    storage_service = StorageService()
    result = storage_service.generate_presigned_upload_url(user_id=str(current_user.user_id))
    return UploadUrlResponse(**result)