import logging
import math
import threading
from typing import ClassVar

import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger("uvicorn.error")


class NoFaceDetectedError(ValueError):
    """Raised when no face is detected in the image."""


class MultipleFacesDetectedError(ValueError):
    """Raised when multiple faces are detected and only one is allowed."""


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
