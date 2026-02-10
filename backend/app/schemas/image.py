from pydantic import BaseModel

class UploadUrlResponse(BaseModel):
    upload_url: str
    bucket: str
    key: str