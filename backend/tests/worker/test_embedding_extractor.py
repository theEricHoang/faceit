"""Unit tests for EmbeddingExtractor."""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.embedding_extractor import (
    EmbeddingExtractor,
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)


class TestExtractEmbedding:
    """Tests for EmbeddingExtractor.extract_embedding()."""

    def setup_method(self):
        """Reset singleton before each test."""
        EmbeddingExtractor._instance = None

    @patch("app.utils.embedding_extractor.FaceAnalysis")
    @patch("app.utils.embedding_extractor.cv2")
    @patch("app.utils.embedding_extractor.np")
    def test_extract_embedding_success(self, mock_np, mock_cv2, mock_face_analysis_cls):
        """Test successful embedding extraction returns embedding and quality score."""
        import numpy as np

        mock_app = MagicMock()
        mock_face_analysis_cls.return_value = mock_app

        fake_embedding = np.random.randn(512).astype(np.float32)
        mock_face = MagicMock()
        mock_face.embedding = fake_embedding
        mock_face.det_score = 0.95
        mock_app.get.return_value = [mock_face]

        mock_np.frombuffer.return_value = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.imdecode.return_value = MagicMock()

        # Use real numpy for the embedding math
        mock_np.uint8 = np.uint8
        mock_np.float32 = np.float32
        mock_np.dot.side_effect = np.dot

        extractor = EmbeddingExtractor()
        embedding, quality_score = extractor.extract_embedding(b"fake-image-bytes")

        assert isinstance(embedding, list)
        assert len(embedding) == 512
        assert quality_score == 0.95
        mock_app.get.assert_called_once()

    @patch("app.utils.embedding_extractor.FaceAnalysis")
    @patch("app.utils.embedding_extractor.cv2")
    @patch("app.utils.embedding_extractor.np")
    def test_extract_embedding_no_face(self, mock_np, mock_cv2, mock_face_analysis_cls):
        """Test NoFaceDetectedError raised when no face is found."""
        mock_app = MagicMock()
        mock_face_analysis_cls.return_value = mock_app
        mock_app.get.return_value = []

        mock_np.frombuffer.return_value = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.imdecode.return_value = MagicMock()

        extractor = EmbeddingExtractor()
        with pytest.raises(NoFaceDetectedError, match="No face detected"):
            extractor.extract_embedding(b"fake-image-bytes")

    @patch("app.utils.embedding_extractor.FaceAnalysis")
    @patch("app.utils.embedding_extractor.cv2")
    @patch("app.utils.embedding_extractor.np")
    def test_extract_embedding_multiple_faces(self, mock_np, mock_cv2, mock_face_analysis_cls):
        """Test MultipleFacesDetectedError raised when multiple faces found."""
        mock_app = MagicMock()
        mock_face_analysis_cls.return_value = mock_app
        mock_app.get.return_value = [MagicMock(), MagicMock()]

        mock_np.frombuffer.return_value = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.imdecode.return_value = MagicMock()

        extractor = EmbeddingExtractor()
        with pytest.raises(MultipleFacesDetectedError, match="Multiple faces detected"):
            extractor.extract_embedding(b"fake-image-bytes")

    @patch("app.utils.embedding_extractor.FaceAnalysis")
    @patch("app.utils.embedding_extractor.cv2")
    @patch("app.utils.embedding_extractor.np")
    def test_extract_embedding_bad_image(self, mock_np, mock_cv2, mock_face_analysis_cls):
        """Test ValueError raised when image cannot be decoded."""
        mock_face_analysis_cls.return_value = MagicMock()

        mock_np.frombuffer.return_value = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.imdecode.return_value = None

        extractor = EmbeddingExtractor()
        with pytest.raises(ValueError, match="Failed to decode image"):
            extractor.extract_embedding(b"not-an-image")


class TestGetInstance:
    """Tests for EmbeddingExtractor.get_instance() singleton."""

    def setup_method(self):
        """Reset singleton before each test."""
        EmbeddingExtractor._instance = None

    def test_get_instance_returns_same_object(self):
        """Test singleton returns the same instance on repeated calls."""
        instance1 = EmbeddingExtractor.get_instance()
        instance2 = EmbeddingExtractor.get_instance()
        assert instance1 is instance2

    def test_get_instance_creates_new_after_reset(self):
        """Test that resetting _instance allows creating a new singleton."""
        instance1 = EmbeddingExtractor.get_instance()
        EmbeddingExtractor._instance = None
        instance2 = EmbeddingExtractor.get_instance()
        assert instance1 is not instance2
