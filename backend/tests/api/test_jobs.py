from unittest.mock import patch, MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.services.job_service import CreateJobError


TEST_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


class TestCreateJobRoute:
    """Tests for POST /jobs."""

    def test_create_enrollment_job_success(self, student_authenticated_client: TestClient):
        """Authenticated student with valid payload should get 201 + job_id."""
        with patch("app.api.routes.jobs.JobService") as MockJobService:
            mock_instance = MagicMock()

            async def mock_create(*args, **kwargs):
                from app.schemas.job import CreateJobResponse
                return CreateJobResponse(job_id=UUID(TEST_JOB_ID))

            mock_instance.create_enrollment_job = mock_create
            MockJobService.return_value = mock_instance

            response = student_authenticated_client.post(
                "/jobs",
                json={"kind": "ENROLLMENT", "bucket": "my-bucket", "key": "photos/img.jpg"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["job_id"] == TEST_JOB_ID

    def test_invalid_kind_returns_422(self, student_authenticated_client: TestClient):
        """A kind other than ENROLLMENT should be rejected by Pydantic validation."""
        response = student_authenticated_client.post(
            "/jobs",
            json={"kind": "ATTENDANCE", "bucket": "b", "key": "k"},
        )
        assert response.status_code == 422

    def test_missing_fields_returns_422(self, student_authenticated_client: TestClient):
        """Missing required fields should return 422."""
        response = student_authenticated_client.post(
            "/jobs",
            json={"kind": "ENROLLMENT"},
        )
        assert response.status_code == 422

    def test_empty_bucket_returns_422(self, student_authenticated_client: TestClient):
        """Empty bucket string should be rejected by min_length validation."""
        response = student_authenticated_client.post(
            "/jobs",
            json={"kind": "ENROLLMENT", "bucket": "", "key": "photos/img.jpg"},
        )
        assert response.status_code == 422

    def test_empty_key_returns_422(self, student_authenticated_client: TestClient):
        """Empty key string should be rejected by min_length validation."""
        response = student_authenticated_client.post(
            "/jobs",
            json={"kind": "ENROLLMENT", "bucket": "my-bucket", "key": ""},
        )
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, test_client: TestClient):
        """Unauthenticated request should get 401."""
        response = test_client.post(
            "/jobs",
            json={"kind": "ENROLLMENT", "bucket": "b", "key": "k"},
        )
        assert response.status_code == 401

    def test_instructor_returns_403(self, authenticated_client: TestClient):
        """Instructor users should get 403 (student-only endpoint)."""
        response = authenticated_client.post(
            "/jobs",
            json={"kind": "ENROLLMENT", "bucket": "b", "key": "k"},
        )
        assert response.status_code == 403

    def test_service_error_returns_400(self, student_authenticated_client: TestClient):
        """CreateJobError from service should map to 400."""
        with patch("app.api.routes.jobs.JobService") as MockJobService:
            mock_instance = MagicMock()

            async def mock_create(*args, **kwargs):
                raise CreateJobError("SQS unavailable")

            mock_instance.create_enrollment_job = mock_create
            MockJobService.return_value = mock_instance

            response = student_authenticated_client.post(
                "/jobs",
                json={"kind": "ENROLLMENT", "bucket": "b", "key": "k"},
            )

        assert response.status_code == 400
        assert "SQS unavailable" in response.json()["detail"]
