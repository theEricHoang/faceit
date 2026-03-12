import logging
import math
import threading
from dataclasses import dataclass
from typing import ClassVar

import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger("uvicorn.error")


class NoFaceDetectedError(ValueError):
    """Raised when no face is detected in the image."""


class MultipleFacesDetectedError(ValueError):
    """Raised when multiple faces are detected and only one is allowed."""


@dataclass
class DetectedFace:
    """Represents a single detected face with its embedding and metadata."""

    embedding: list[float]
    quality_score: float
    face_index: int
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


class EmbeddingExtractor:
    """Extracts face embeddings using InsightFace ArcFace model."""

    _instance: ClassVar["EmbeddingExtractor | None"] = None
    _init_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self):
        """Initialize InsightFace analyzer (loads model on first use)."""
        self.app: FaceAnalysis | None = None
        self._load_lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        """Lazy-load the InsightFace app on first call (thread-safe)."""
        if self.app is None:
            with self._load_lock:
                if self.app is None:
                    logger.info("Loading InsightFace model (first initialization)...")
                    self.app = FaceAnalysis(
                        name="buffalo_l",  # L-model: high accuracy, outputs 512-dim embeddings
                        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                    )
                    # ctx_id=-1 uses CPU; CUDAExecutionProvider in the providers
                    # list will still enable GPU when available
                    self.app.prepare(ctx_id=-1)

    @classmethod
    def get_instance(cls) -> "EmbeddingExtractor":
        """Get singleton instance (model loads on first access)."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def extract_embedding(self, image_bytes: bytes) -> tuple[list[float], float]:
        """
        Extract face embedding from image bytes.

        Returns:
            (embedding: list[float], quality_score: float)
            - embedding: 512-dimensional vector normalized to unit length
            - quality_score: confidence score (0-1) for the detected face

        Raises:
            ValueError: If no face detected in image or image decode fails
        """
        self._ensure_loaded()

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Failed to decode image")

        # Detect faces
        faces = self.app.get(image)

        if not faces:
            raise NoFaceDetectedError("No face detected in image")

        if len(faces) > 1:
            raise MultipleFacesDetectedError(
                f"Multiple faces detected ({len(faces)})"
            )

        face = faces[0]

        # Extract embedding (already normalized by InsightFace)
        embedding_vector = face.embedding.astype(np.float32)
        norm = math.sqrt(float(np.dot(embedding_vector, embedding_vector))) or 1.0
        embedding = (embedding_vector / norm).tolist()

        # Quality score based on detection confidence
        quality_score = float(face.det_score)

        return embedding, quality_score

    def extract_multiple_embeddings(
        self, image_bytes: bytes, min_quality: float = 0.0
    ) -> list[DetectedFace]:
        """
        Extract embeddings for ALL faces detected in an image.

        This is used for classroom attendance photos where multiple
        students may be present.

        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            min_quality: Minimum detection confidence to include a face (0-1).
                         Faces below this threshold are skipped.

        Returns:
            List of DetectedFace objects, each containing:
            - embedding: 512-dim normalized vector
            - quality_score: detection confidence (0-1)
            - face_index: position in the original detection order
            - bbox: bounding box coordinates (x1, y1, x2, y2)

        Raises:
            ValueError: If image cannot be decoded.
            NoFaceDetectedError: If no faces are detected in the image.
        """
        self._ensure_loaded()

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Failed to decode image")

        # Detect all faces
        faces = self.app.get(image)

        if not faces:
            raise NoFaceDetectedError("No faces detected in image")

        detected_faces: list[DetectedFace] = []

        for idx, face in enumerate(faces):
            quality_score = float(face.det_score)

            # Skip low-quality detections
            if quality_score < min_quality:
                logger.debug(
                    "Skipping face %d with quality %.3f (below threshold %.3f)",
                    idx, quality_score, min_quality
                )
                continue

            # Extract and normalize embedding
            embedding_vector = face.embedding.astype(np.float32)
            norm = math.sqrt(float(np.dot(embedding_vector, embedding_vector))) or 1.0
            embedding = (embedding_vector / norm).tolist()

            # Get bounding box (InsightFace returns [x1, y1, x2, y2])
            bbox = tuple(int(coord) for coord in face.bbox[:4])

            detected_faces.append(
                DetectedFace(
                    embedding=embedding,
                    quality_score=quality_score,
                    face_index=idx,
                    bbox=bbox,
                )
            )

        if not detected_faces:
            raise NoFaceDetectedError(
                f"No faces above quality threshold {min_quality} detected"
            )

        logger.info(
            "Detected %d faces (filtered from %d total detections)",
            len(detected_faces), len(faces)
        )

        return detected_faces
