"""Unit tests for RecognitionService."""

import math
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.services.recognition_service import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EnrolledEmbedding,
    FaceMatch,
    NoEnrolledStudentsError,
    RecognitionService,
    RecognitionServiceError,
)
from app.utils.embedding_extractor import DetectedFace


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------

CLASS_ID = "11111111-1111-1111-1111-111111111111"
STUDENT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STUDENT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _normalized_embedding(values: list[float]) -> list[float]:
    """Normalize a vector to unit length."""
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


# Sample embeddings (normalized)
EMBEDDING_A = _normalized_embedding([1.0, 0.0, 0.0] + [0.0] * 509)  # Points in x direction
EMBEDDING_B = _normalized_embedding([0.0, 1.0, 0.0] + [0.0] * 509)  # Points in y direction
EMBEDDING_A_SIMILAR = _normalized_embedding([0.95, 0.1, 0.0] + [0.0] * 509)  # Close to A


# ---------------------------------------------------------------------------
# Mock Helpers
# ---------------------------------------------------------------------------


class MockResponse:
    """Lightweight stand-in for Supabase execute() results."""

    def __init__(self, data):
        self.data = data


def _build_mock_client(enrollment_data, embeddings_data):
    """Build a MagicMock Supabase client for recognition tests."""
    client = MagicMock()

    def table_router(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain

        if table_name == "student_classes":
            chain.execute.return_value = MockResponse(enrollment_data)
        elif table_name == "face_embeddings":
            chain.execute.return_value = MockResponse(embeddings_data)
        else:
            chain.execute.return_value = MockResponse(None)

        return chain

    client.table.side_effect = table_router
    return client


# ---------------------------------------------------------------------------
# Tests: Cosine Similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """Tests for the static _cosine_similarity method."""

    def test_identical_vectors_return_one(self):
        """Identical normalized vectors should have similarity = 1.0"""
        vec = _normalized_embedding([1.0, 2.0, 3.0] + [0.0] * 509)
        similarity = RecognitionService._cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001

    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors should have similarity = 0.0"""
        vec_a = _normalized_embedding([1.0, 0.0, 0.0] + [0.0] * 509)
        vec_b = _normalized_embedding([0.0, 1.0, 0.0] + [0.0] * 509)
        similarity = RecognitionService._cosine_similarity(vec_a, vec_b)
        assert abs(similarity) < 0.0001

    def test_opposite_vectors_return_negative_one(self):
        """Opposite vectors should have similarity = -1.0"""
        vec_a = _normalized_embedding([1.0, 0.0, 0.0] + [0.0] * 509)
        vec_b = _normalized_embedding([-1.0, 0.0, 0.0] + [0.0] * 509)
        similarity = RecognitionService._cosine_similarity(vec_a, vec_b)
        assert abs(similarity - (-1.0)) < 0.0001

    def test_similar_vectors_return_high_similarity(self):
        """Similar vectors should have high similarity (> 0.9)"""
        vec_a = _normalized_embedding([1.0, 0.0, 0.0] + [0.0] * 509)
        vec_b = _normalized_embedding([0.95, 0.1, 0.0] + [0.0] * 509)
        similarity = RecognitionService._cosine_similarity(vec_a, vec_b)
        assert similarity > 0.9

    def test_dimension_mismatch_raises_error(self):
        """Vectors of different dimensions should raise ValueError"""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 0.0]
        with pytest.raises(ValueError, match="dimension mismatch"):
            RecognitionService._cosine_similarity(vec_a, vec_b)


# ---------------------------------------------------------------------------
# Tests: Face Matching
# ---------------------------------------------------------------------------


class TestMatchFaces:
    """Tests for the match_faces method."""

    def test_exact_match_returns_student_id(self):
        """When face embedding exactly matches enrolled, return that student."""
        enrolled = [
            EnrolledEmbedding(student_id=STUDENT_A_ID, embedding=EMBEDDING_A, model="v1"),
            EnrolledEmbedding(student_id=STUDENT_B_ID, embedding=EMBEDDING_B, model="v1"),
        ]
        detected = [
            DetectedFace(
                embedding=EMBEDDING_A,  # Exact match to student A
                quality_score=0.95,
                face_index=0,
                bbox=(0, 0, 100, 100),
            )
        ]

        service = RecognitionService(client=MagicMock(), similarity_threshold=0.6)
        matches = service.match_faces(detected, enrolled)

        assert len(matches) == 1
        assert matches[0].student_id == STUDENT_A_ID
        assert matches[0].confidence > 0.99  # Exact match

    def test_similar_but_not_exact_match(self):
        """Face similar to enrolled (above threshold) should match."""
        enrolled = [
            EnrolledEmbedding(student_id=STUDENT_A_ID, embedding=EMBEDDING_A, model="v1"),
        ]
        detected = [
            DetectedFace(
                embedding=EMBEDDING_A_SIMILAR,  # Similar to A
                quality_score=0.9,
                face_index=0,
                bbox=(0, 0, 100, 100),
            )
        ]

        service = RecognitionService(client=MagicMock(), similarity_threshold=0.6)
        matches = service.match_faces(detected, enrolled)

        assert len(matches) == 1
        assert matches[0].student_id == STUDENT_A_ID
        assert matches[0].confidence > 0.6  # Above threshold

    def test_no_match_returns_unknown(self):
        """Face not matching any enrolled student returns student_id=None (UNKNOWN)."""
        enrolled = [
            EnrolledEmbedding(student_id=STUDENT_A_ID, embedding=EMBEDDING_A, model="v1"),
        ]
        detected = [
            DetectedFace(
                embedding=EMBEDDING_B,  # Orthogonal to A - no match
                quality_score=0.9,
                face_index=0,
                bbox=(0, 0, 100, 100),
            )
        ]

        service = RecognitionService(client=MagicMock(), similarity_threshold=0.6)
        matches = service.match_faces(detected, enrolled)

        assert len(matches) == 1
        assert matches[0].student_id is None  # UNKNOWN
        assert matches[0].face_index == 0

    def test_multiple_faces_matched_correctly(self):
        """Multiple detected faces should each be matched independently."""
        enrolled = [
            EnrolledEmbedding(student_id=STUDENT_A_ID, embedding=EMBEDDING_A, model="v1"),
            EnrolledEmbedding(student_id=STUDENT_B_ID, embedding=EMBEDDING_B, model="v1"),
        ]
        detected = [
            DetectedFace(embedding=EMBEDDING_A, quality_score=0.95, face_index=0, bbox=(0, 0, 100, 100)),
            DetectedFace(embedding=EMBEDDING_B, quality_score=0.90, face_index=1, bbox=(100, 0, 200, 100)),
        ]

        service = RecognitionService(client=MagicMock(), similarity_threshold=0.6)
        matches = service.match_faces(detected, enrolled)

        assert len(matches) == 2
        assert matches[0].student_id == STUDENT_A_ID
        assert matches[1].student_id == STUDENT_B_ID

    def test_threshold_boundary_below(self):
        """Face just below threshold should not match."""
        # Create an embedding that will give ~0.5 similarity
        mixed = _normalized_embedding([0.5, 0.5, 0.5, 0.5] + [0.0] * 508)
        enrolled = [
            EnrolledEmbedding(student_id=STUDENT_A_ID, embedding=EMBEDDING_A, model="v1"),
        ]
        detected = [
            DetectedFace(embedding=mixed, quality_score=0.9, face_index=0, bbox=(0, 0, 100, 100)),
        ]

        service = RecognitionService(client=MagicMock(), similarity_threshold=0.6)
        matches = service.match_faces(detected, enrolled)

        # Should be UNKNOWN since similarity < threshold
        assert matches[0].student_id is None


# ---------------------------------------------------------------------------
# Tests: Get Enrolled Embeddings
# ---------------------------------------------------------------------------


class TestGetEnrolledEmbeddings:
    """Tests for fetching enrolled embeddings from database."""

    def test_happy_path_returns_embeddings(self):
        """Successfully fetches embeddings for enrolled students."""
        mock_client = _build_mock_client(
            enrollment_data=[
                {"student_id": STUDENT_A_ID},
                {"student_id": STUDENT_B_ID},
            ],
            embeddings_data=[
                {"user_id": STUDENT_A_ID, "embedding": EMBEDDING_A, "model": "v1"},
                {"user_id": STUDENT_B_ID, "embedding": EMBEDDING_B, "model": "v1"},
            ],
        )

        service = RecognitionService(client=mock_client)
        embeddings = service.get_enrolled_embeddings(CLASS_ID)

        assert len(embeddings) == 2
        assert embeddings[0].student_id == STUDENT_A_ID
        assert embeddings[1].student_id == STUDENT_B_ID

    def test_no_enrolled_students_raises_error(self):
        """Raises NoEnrolledStudentsError when class has no students."""
        mock_client = _build_mock_client(
            enrollment_data=[],  # No students
            embeddings_data=[],
        )

        service = RecognitionService(client=mock_client)
        with pytest.raises(NoEnrolledStudentsError):
            service.get_enrolled_embeddings(CLASS_ID)

    def test_no_embeddings_raises_error(self):
        """Raises NoEnrolledStudentsError when students have no face embeddings."""
        mock_client = _build_mock_client(
            enrollment_data=[{"student_id": STUDENT_A_ID}],
            embeddings_data=[],  # No embeddings
        )

        service = RecognitionService(client=mock_client)
        with pytest.raises(NoEnrolledStudentsError):
            service.get_enrolled_embeddings(CLASS_ID)


# ---------------------------------------------------------------------------
# Tests: Recognize Class Photo (Integration)
# ---------------------------------------------------------------------------


class TestRecognizeClassPhoto:
    """Tests for the high-level recognize_class_photo method."""

    def test_returns_matches_and_summary(self):
        """Returns both match list and summary dict."""
        mock_client = _build_mock_client(
            enrollment_data=[{"student_id": STUDENT_A_ID}],
            embeddings_data=[
                {"user_id": STUDENT_A_ID, "embedding": EMBEDDING_A, "model": "v1"},
            ],
        )

        detected = [
            DetectedFace(embedding=EMBEDDING_A, quality_score=0.95, face_index=0, bbox=(0, 0, 100, 100)),
            DetectedFace(embedding=EMBEDDING_B, quality_score=0.90, face_index=1, bbox=(100, 0, 200, 100)),
        ]

        service = RecognitionService(client=mock_client)
        matches, summary = service.recognize_class_photo(detected, CLASS_ID)

        assert len(matches) == 2
        assert summary["total_faces"] == 2
        assert summary["present_count"] == 1  # Only student A matched
        assert summary["unknown_count"] == 1  # Student B not enrolled
        assert summary["enrolled_count"] == 1
