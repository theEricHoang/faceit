import uuid
import boto3
from botocore.config import Config

from app.core.config import get_settings


class StorageService:
    def __init__(self):
        settings = get_settings()
        self.bucket = settings.s3_enrollment_bucket
        self.expiry = settings.s3_presigned_url_expiry
        if settings.aws_profile:
            session = boto3.Session(profile_name=settings.aws_profile)
        else:
            session = boto3.Session()
        
        self.s3_client = session.client(
            "s3",
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )

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