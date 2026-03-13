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
        self, user_id: str, job_id: str, file_extension: str = "jpg"
    ) -> dict:
        """Generate a pre-signed URL for uploading an enrollment photo.
        
        Args:
            user_id: The user ID who is enrolling.
            job_id: The job ID for this enrollment (used in S3 key).
            file_extension: File extension (default: jpg).
        
        Returns:
            Dict with upload_url, bucket, and key.
        """
        # Key format: enrollments/{user_id}/{job_id}.{extension}
        key = f"enrollments/{user_id}/{job_id}.{file_extension}"

        # Map file extension to proper MIME type
        content_type = "image/jpeg" if file_extension in ("jpg", "jpeg") else f"image/{file_extension}"

        upload_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
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
        self,
        class_id: str,
        instructor_id: str,
        session_id: str,
        file_extension: str = "jpg",
    ) -> dict:
        """Generate a pre-signed URL for uploading one photo into an attendance session."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key_prefix = (
            f"attendance-photos/class-{class_id}/"
            f"instructor-{instructor_id}/session-{session_id}/"
        )
        key = f"{key_prefix}{timestamp}-{uuid.uuid4()}.{file_extension}"

        content_type = "image/jpeg" if file_extension == "jpg" else f"image/{file_extension}"

        upload_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.attendance_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=self.attendance_expiry,
            HttpMethod="PUT",
        )

        return {
            "upload_url": upload_url,
            "bucket": self.attendance_bucket,
            "key": key,
            "key_prefix": key_prefix,
        }
