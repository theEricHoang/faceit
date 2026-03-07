from unittest.mock import patch, MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.services.job_service import CreateJobError, JobNotFoundError


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


class TestGetJobStatusRoute:
    """Tests for GET /jobs/{job_id}."""

    def test_get_job_status_success(self, student_authenticated_client: TestClient):
        """Authenticated student should get 200 with job status fields."""
        with patch("app.api.routes.jobs.JobService") as MockJobService:
            mock_instance = MagicMock()

            async def mock_get_status(*args, **kwargs):
                from app.schemas.job import JobStatusResponse
                return JobStatusResponse(
                    job_id=UUID(TEST_JOB_ID),
                    status="SUCCEEDED",
                    kind="ENROLLMENT",
                    error_message=None,
                    updated_at="2026-03-04T12:00:00Z",
                )

            mock_instance.get_job_status = mock_get_status
            MockJobService.return_value = mock_instance

            response = student_authenticated_client.get(f"/jobs/{TEST_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == TEST_JOB_ID
        assert data["status"] == "SUCCEEDED"
        assert data["kind"] == "ENROLLMENT"
        assert data["error_message"] is None
        assert "updated_at" in data

    def test_get_failed_job_includes_error_message(self, student_authenticated_client: TestClient):
        """A FAILED job should include error_message in the response."""
        with patch("app.api.routes.jobs.JobService") as MockJobService:
            mock_instance = MagicMock()

            async def mock_get_status(*args, **kwargs):
                from app.schemas.job import JobStatusResponse
                return JobStatusResponse(
                    job_id=UUID(TEST_JOB_ID),
                    status="FAILED",
                    kind="ENROLLMENT",
                    error_message="NO_FACE_DETECTED: no face found in image",
                    updated_at="2026-03-04T12:00:00Z",
                )

            mock_instance.get_job_status = mock_get_status
            MockJobService.return_value = mock_instance

            response = student_authenticated_client.get(f"/jobs/{TEST_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILED"
        assert data["error_message"] == "NO_FACE_DETECTED: no face found in image"

    def test_job_not_found_returns_404(self, student_authenticated_client: TestClient):
        """Non-existent job or wrong owner should return 404."""
        with patch("app.api.routes.jobs.JobService") as MockJobService:
            mock_instance = MagicMock()

            async def mock_get_status(*args, **kwargs):
                raise JobNotFoundError("Job not found")

            mock_instance.get_job_status = mock_get_status
            MockJobService.return_value = mock_instance

            response = student_authenticated_client.get(f"/jobs/{TEST_JOB_ID}")

        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    def test_invalid_job_id_returns_422(self, student_authenticated_client: TestClient):
        """A non-UUID job_id should be rejected by FastAPI validation."""
        response = student_authenticated_client.get("/jobs/not-a-uuid")
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, test_client: TestClient):
        """Unauthenticated request should get 401."""
        response = test_client.get(f"/jobs/{TEST_JOB_ID}")
        assert response.status_code == 401

    def test_instructor_returns_403(self, authenticated_client: TestClient):
        """Instructor users should get 403 (student-only endpoint)."""
        response = authenticated_client.get(f"/jobs/{TEST_JOB_ID}")
        assert response.status_code == 403
