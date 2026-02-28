import uuid
from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.aws import get_s3_client


class StorageService:
    def __init__(self, s3_client=None):
        settings = get_settings()
        self.bucket = settings.s3_enrollment_bucket
        self.expiry = settings.s3_presigned_url_expiry
        self.attendance_bucket = settings.s3_attendance_bucket
        self.attendance_expiry = settings.s3_attendance_presigned_url_expiry
        self.s3_client = s3_client or get_s3_client()

    def generate_presigned_upload_url(
        self, user_id: str, file_extension: str = "jpg"
    ) -> dict:
        """Generate a pre-signed URL for uploading an enrollment photo."""
        key = f"enrollment-photos/{user_id}/{uuid.uuid4()}.{file_extension}"

        upload_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": f"image/{file_extension}",
            },
            ExpiresIn=self.expiry,
            HttpMethod="PUT",
        )

        return {
            "upload_url": upload_url,
            "bucket": self.bucket,
            "key": key,
        }

    def generate_attendance_presigned_upload_url(
        self, class_id: str, instructor_id: str, file_extension: str = "jpg"
    ) -> dict:
        """Generate a pre-signed URL for uploading an attendance class photo."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = (
            f"attendance-photos/class-{class_id}/"
            f"instructor-{instructor_id}/{timestamp}-{uuid.uuid4()}.{file_extension}"
        )

        upload_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.attendance_bucket,
                "Key": key,
                "ContentType": f"image/{file_extension}",
            },
            ExpiresIn=self.attendance_expiry,
            HttpMethod="PUT",
        )

        return {
            "upload_url": upload_url,
            "bucket": self.attendance_bucket,
            "key": key,
        }
