from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestGetPhotoUploadUrl:
    """Tests for POST /enrollments/upload-url"""

    def test_returns_presigned_url_for_authenticated_user(
        self, student_authenticated_client: TestClient
    ):
        """Authenticated student should receive upload URL, bucket, key, and job_id."""
        mock_response = {
            "upload_url": "https://test-bucket.s3.amazonaws.com/presigned-url",
            "bucket": "test-bucket",
            "key": "enrollments/user-123/job-456.jpg",
        }

        with patch(
            "app.api.routes.enrollment.StorageService"
        ) as MockStorageService, patch(
            "app.api.routes.enrollment.JobService"
        ) as MockJobService:
            mock_storage = MagicMock()
            mock_storage.generate_presigned_upload_url.return_value = mock_response
            MockStorageService.return_value = mock_storage
            
            mock_job = MagicMock()
            mock_job.client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "job-456"}]
            MockJobService.return_value = mock_job

            response = student_authenticated_client.post("/enrollments/upload-url")

        assert response.status_code == 200
        data = response.json()
        assert data["upload_url"] == mock_response["upload_url"]
        assert data["bucket"] == mock_response["bucket"]
        assert data["key"] == mock_response["key"]
        assert "job_id" in data

    def test_key_contains_user_id(self, student_authenticated_client: TestClient, mock_student_user):
        """The returned key should be namespaced with the user's ID."""
        with patch(
            "app.api.routes.enrollment.StorageService"
        ) as MockStorageService, patch(
            "app.api.routes.enrollment.JobService"
        ) as MockJobService:
            mock_storage = MagicMock()
            mock_storage.generate_presigned_upload_url.return_value = {
                "upload_url": "https://example.com/url",
                "bucket": "bucket",
                "key": f"enrollments/{mock_student_user.user_id}/job-123.jpg",
            }
            MockStorageService.return_value = mock_storage
            
            mock_job = MagicMock()
            mock_job.client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "job-123"}]
            MockJobService.return_value = mock_job

            response = student_authenticated_client.post("/enrollments/upload-url")

        assert response.status_code == 200
        assert str(mock_student_user.user_id) in response.json()["key"]

    def test_unauthenticated_request_returns_401(self, test_client: TestClient):
        """Unauthenticated requests should be rejected."""
        response = test_client.post("/enrollments/upload-url")
        assert response.status_code == 401