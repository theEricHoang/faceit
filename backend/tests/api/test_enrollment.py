from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestGetPhotoUploadUrl:
    """Tests for POST /enrollment/photos/upload-url"""

    def test_returns_presigned_url_for_authenticated_user(
        self, student_authenticated_client: TestClient
    ):
        """Authenticated student should receive upload URL, bucket, and key."""
        mock_response = {
            "upload_url": "https://test-bucket.s3.amazonaws.com/presigned-url",
            "bucket": "test-bucket",
            "key": "enrollment-photos/user-123/photo.jpg",
        }

        with patch(
            "app.api.routes.enrollment.StorageService"
        ) as MockStorageService:
            mock_instance = MagicMock()
            mock_instance.generate_presigned_upload_url.return_value = mock_response
            MockStorageService.return_value = mock_instance

            response = student_authenticated_client.post("/enrollment/photos/upload-url")

        assert response.status_code == 200
        data = response.json()
        assert data["upload_url"] == mock_response["upload_url"]
        assert data["bucket"] == mock_response["bucket"]
        assert data["key"] == mock_response["key"]

    def test_key_contains_user_id(self, student_authenticated_client: TestClient, mock_student_user):
        """The returned key should be namespaced with the user's ID."""
        with patch(
            "app.api.routes.enrollment.StorageService"
        ) as MockStorageService:
            mock_instance = MagicMock()
            mock_instance.generate_presigned_upload_url.return_value = {
                "upload_url": "https://example.com/url",
                "bucket": "bucket",
                "key": f"enrollment-photos/{mock_student_user.user_id}/photo.jpg",
            }
            MockStorageService.return_value = mock_instance

            response = student_authenticated_client.post("/enrollment/photos/upload-url")

        assert response.status_code == 200
        assert str(mock_student_user.user_id) in response.json()["key"]

    def test_unauthenticated_request_returns_401(self, test_client: TestClient):
        """Unauthenticated requests should be rejected."""
        response = test_client.post("/enrollment/photos/upload-url")
        assert response.status_code == 401