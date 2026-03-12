"""
Face recognition service for matching detected faces against enrolled students.

This service implements the core matching logic for attendance tracking:
1. Fetches enrolled students for a class from `student_classes`
2. Retrieves their face embeddings from `face_embeddings`
3. Computes cosine similarity between detected faces and enrolled embeddings
4. Returns matches above the configured threshold

COSINE SIMILARITY THRESHOLD:
- 0.6 is a common threshold for face recognition (strict)
- 0.5 allows more matches but may have false positives
- We use 0.6 as default for attendance (prefer accuracy over recall)

Reference: Most face recognition papers use 0.6-0.7 for ArcFace embeddings.
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

from supabase import Client

from app.db.supabase import get_supabase_client
from app.utils.embedding_extractor import DetectedFace

logger = logging.getLogger("uvicorn.error")

# Default cosine similarity threshold for face matching.
# Faces with similarity above this threshold are considered matches.
# ArcFace embeddings typically use 0.6-0.7 for good accuracy.
DEFAULT_SIMILARITY_THRESHOLD = 0.6


class RecognitionServiceError(Exception):
    """Base exception for recognition service errors."""

    pass


class NoEnrolledStudentsError(RecognitionServiceError):
    """Raised when a class has no enrolled students with embeddings."""

    pass


@dataclass
class FaceMatch:
    """Result of matching a detected face against enrolled embeddings.

    Attributes:
        face_index: Index of the face in the detection order.
        student_id: Matched student's user ID (None if no match found).
        confidence: Cosine similarity score (0-1). Higher = more similar.
        quality_score: Detection quality from the face detector.
    """

    face_index: int
    student_id: Optional[str]
    confidence: Optional[float]
    quality_score: float


@dataclass
class EnrolledEmbedding:
    """A student's enrolled face embedding."""

    student_id: str
    embedding: list[float]
    model: str


class RecognitionService:
    """
    Service for matching detected faces against a class's enrolled students.

    How it works:
    1. Given a class_id, fetch all students enrolled via `student_classes`
    2. For each enrolled student, fetch their face embedding from `face_embeddings`
    3. For each detected face, compute cosine similarity against all enrolled embeddings
    4. Return the best match (if above threshold) or mark as UNKNOWN

    Cosine Similarity:
    - Measures the angle between two vectors (embeddings)
    - Range: -1 (opposite) to 1 (identical)
    - Formula: cos(θ) = A·B / (||A|| × ||B||)
    - For normalized embeddings (already ||v|| = 1): just the dot product A·B
    """

    def __init__(
        self,
        client: Client | None = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self.client = client or get_supabase_client()
        self.similarity_threshold = similarity_threshold

    def get_enrolled_embeddings(self, class_id: str) -> list[EnrolledEmbedding]:
        """
        Fetch face embeddings for all students enrolled in a class.

        Steps:
        1. Query `student_classes` to get student_ids for the class
        2. Query `face_embeddings` for those student_ids
        3. Return list of EnrolledEmbedding objects

        Args:
            class_id: The class UUID to fetch embeddings for.

        Returns:
            List of EnrolledEmbedding objects.

        Raises:
            NoEnrolledStudentsError: If no students have enrolled embeddings.
            RecognitionServiceError: On database errors.
        """
        try:
            # Step 1: Get enrolled student IDs for this class
            enrollment_result = (
                self.client.table("student_classes")
                .select("student_id")
                .eq("class_id", class_id)
                .execute()
            )

            if not enrollment_result.data:
                raise NoEnrolledStudentsError(
                    f"No students enrolled in class {class_id}"
                )

            student_ids = [row["student_id"] for row in enrollment_result.data]
            logger.info(
                "Found %d enrolled students for class %s",
                len(student_ids), class_id
            )

            # Step 2: Fetch embeddings for enrolled students
            # Note: Not all students may have face embeddings (not yet enrolled face)
            embeddings_result = (
                self.client.table("face_embeddings")
                .select("user_id, embedding, model")
                .in_("user_id", student_ids)
                .execute()
            )

            if not embeddings_result.data:
                raise NoEnrolledStudentsError(
                    f"No face embeddings found for students in class {class_id}"
                )

            enrolled_embeddings = [
                EnrolledEmbedding(
                    student_id=row["user_id"],
                    embedding=row["embedding"],
                    model=row["model"],
                )
                for row in embeddings_result.data
            ]

            logger.info(
                "Loaded %d face embeddings for class %s",
                len(enrolled_embeddings), class_id
            )

            return enrolled_embeddings

        except NoEnrolledStudentsError:
            raise
        except Exception as e:
            logger.exception("Failed to fetch enrolled embeddings for class %s", class_id)
            raise RecognitionServiceError(
                f"Failed to fetch enrolled embeddings: {e}"
            ) from e

    def match_faces(
        self,
        detected_faces: list[DetectedFace],
        enrolled_embeddings: list[EnrolledEmbedding],
    ) -> list[FaceMatch]:
        """
        Match detected faces against enrolled student embeddings.

        For each detected face:
        1. Compute cosine similarity against all enrolled embeddings
        2. Find the best match (highest similarity)
        3. If best match >= threshold, return that student
        4. Otherwise, mark as UNKNOWN (student_id = None)

        Args:
            detected_faces: List of faces detected in the class photo.
            enrolled_embeddings: List of enrolled student embeddings.

        Returns:
            List of FaceMatch objects (one per detected face).
        """
        matches: list[FaceMatch] = []

        for face in detected_faces:
            best_match: Optional[str] = None
            best_similarity: float = -1.0

            # Compare against all enrolled embeddings
            for enrolled in enrolled_embeddings:
                similarity = self._cosine_similarity(
                    face.embedding, enrolled.embedding
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = enrolled.student_id

            # Check if best match exceeds threshold
            if best_similarity >= self.similarity_threshold:
                matches.append(
                    FaceMatch(
                        face_index=face.face_index,
                        student_id=best_match,
                        confidence=best_similarity,
                        quality_score=face.quality_score,
                    )
                )
                logger.debug(
                    "Face %d matched to student %s (confidence: %.3f)",
                    face.face_index, best_match, best_similarity
                )
            else:
                # No match above threshold - mark as UNKNOWN
                matches.append(
                    FaceMatch(
                        face_index=face.face_index,
                        student_id=None,  # UNKNOWN
                        confidence=best_similarity if best_similarity > 0 else None,
                        quality_score=face.quality_score,
                    )
                )
                logger.debug(
                    "Face %d: no match found (best: %.3f, threshold: %.3f)",
                    face.face_index, best_similarity, self.similarity_threshold
                )

        return matches

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """
        Compute cosine similarity between two embedding vectors.

        Formula: cos(θ) = A·B / (||A|| × ||B||)

        Since our embeddings are already normalized (||v|| = 1),
        this simplifies to just the dot product: A·B

        Args:
            vec_a: First embedding vector (512-dim).
            vec_b: Second embedding vector (512-dim).

        Returns:
            Similarity score from -1 (opposite) to 1 (identical).
        """
        if len(vec_a) != len(vec_b):
            raise ValueError(
                f"Embedding dimension mismatch: {len(vec_a)} vs {len(vec_b)}"
            )

        # Dot product (embeddings are pre-normalized)
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))

        # Clamp to [-1, 1] to handle floating point precision issues
        return max(-1.0, min(1.0, dot_product))

    def recognize_class_photo(
        self, detected_faces: list[DetectedFace], class_id: str
    ) -> tuple[list[FaceMatch], dict]:
        """
        High-level method to recognize all faces in a class photo.

        This combines embedding retrieval and face matching into one call.

        Args:
            detected_faces: Faces detected in the uploaded class photo.
            class_id: The class for which attendance is being taken.

        Returns:
            Tuple of (matches, summary):
            - matches: List of FaceMatch objects
            - summary: Dict with {total_faces, present_count, unknown_count}

        Raises:
            NoEnrolledStudentsError: If class has no enrolled embeddings.
            RecognitionServiceError: On database errors.
        """
        # Fetch enrolled embeddings
        enrolled_embeddings = self.get_enrolled_embeddings(class_id)

        # Match faces
        matches = self.match_faces(detected_faces, enrolled_embeddings)

        # Compute summary
        present_count = sum(1 for m in matches if m.student_id is not None)
        unknown_count = len(matches) - present_count

        summary = {
            "total_faces": len(matches),
            "present_count": present_count,
            "unknown_count": unknown_count,
            "enrolled_count": len(enrolled_embeddings),
        }

        logger.info(
            "Recognition complete: %d faces, %d present, %d unknown",
            summary["total_faces"], summary["present_count"], summary["unknown_count"]
        )

        return matches, summary
