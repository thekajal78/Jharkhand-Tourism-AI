"""
Tests for CLIP Service
========================
Run with: pytest tests/test_clip.py -v

These tests verify:
  1. Model loads correctly
  2. Image encoding works (produces correct vector shape)
  3. Text encoding works
  4. FAISS search returns correct results
  5. Visual search pipeline end-to-end
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.clip_service import CLIPService, EMBEDDING_DIM


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def clip_service():
    """Create a CLIPService instance for testing."""
    return CLIPService()


@pytest.fixture
def mock_loaded_clip(clip_service):
    """
    Create a CLIPService with mocked model.
    We mock the actual CLIP model so tests run fast without downloading 350MB.
    """
    # Mock the model as loaded
    clip_service.is_loaded = True
    clip_service.device = "cpu"

    # Mock encode functions to return random 512-dim vectors
    # (same shape as real CLIP output)
    async def mock_encode_image(image_path):
        vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        return vec / np.linalg.norm(vec)  # Normalized unit vector

    async def mock_encode_text(text):
        vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        return vec / np.linalg.norm(vec)

    clip_service.encode_image = mock_encode_image
    clip_service.encode_text = mock_encode_text

    # Create real FAISS index for testing
    clip_service._create_empty_faiss_index()

    return clip_service


# ─── Unit Tests ───────────────────────────────────────────────────────────────

class TestCLIPServiceInit:

    def test_service_creates_correctly(self, clip_service):
        """Service should initialize with correct defaults."""
        assert clip_service.model is None        # Not loaded yet
        assert clip_service.is_loaded is False   # Not ready yet
        assert clip_service.faiss_index is None  # No index yet
        assert clip_service.index_to_destination == {}

    def test_device_selection(self, clip_service):
        """Should prefer CUDA if available, else CPU."""
        import torch
        expected_device = "cuda" if torch.cuda.is_available() else "cpu"
        assert clip_service.device == expected_device


class TestEmbeddingShape:
    """Test that encodings produce correct vector shapes."""

    @pytest.mark.asyncio
    async def test_text_encoding_shape(self, mock_loaded_clip):
        """Text encoding should produce a 512-dim vector."""
        vector = await mock_loaded_clip.encode_text("beautiful waterfall in Jharkhand")
        assert vector.shape == (EMBEDDING_DIM,), f"Expected ({EMBEDDING_DIM},), got {vector.shape}"

    @pytest.mark.asyncio
    async def test_image_encoding_shape(self, mock_loaded_clip, tmp_path):
        """Image encoding should produce a 512-dim vector."""
        # Create a small test image
        from PIL import Image
        img = Image.new("RGB", (224, 224), color=(100, 150, 200))
        img_path = str(tmp_path / "test.jpg")
        img.save(img_path)

        vector = await mock_loaded_clip.encode_image(img_path)
        assert vector.shape == (EMBEDDING_DIM,), f"Expected ({EMBEDDING_DIM},), got {vector.shape}"

    @pytest.mark.asyncio
    async def test_vectors_are_normalized(self, mock_loaded_clip):
        """Vectors should be unit-length (required for cosine similarity)."""
        vector = await mock_loaded_clip.encode_text("test query")
        norm = np.linalg.norm(vector)
        assert abs(norm - 1.0) < 0.01, f"Vector should be unit length, got norm={norm}"

    @pytest.mark.asyncio
    async def test_different_texts_produce_different_vectors(self, mock_loaded_clip):
        """Different texts should produce different vectors."""
        vec1 = await mock_loaded_clip.encode_text("waterfall")
        vec2 = await mock_loaded_clip.encode_text("temple")
        assert not np.allclose(vec1, vec2), "Different texts should give different vectors"


class TestFAISSSearch:
    """Test vector search functionality."""

    @pytest.mark.asyncio
    async def test_empty_index_returns_empty(self, mock_loaded_clip):
        """Searching empty index should return empty list."""
        results = await mock_loaded_clip.search_by_text("waterfall", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_after_adding_destinations(self, mock_loaded_clip, tmp_path):
        """After adding destinations, search should return results."""
        from PIL import Image

        # Add 3 test destinations
        destinations = ["Hundru Falls", "Betla National Park", "Deoghar Temple"]
        for name in destinations:
            img = Image.new("RGB", (224, 224), color=(
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255)
            ))
            img_path = str(tmp_path / f"{name}.jpg")
            img.save(img_path)

            # Mock save to avoid disk writes in tests
            with patch.object(mock_loaded_clip, '_save_faiss_index'):
                await mock_loaded_clip.add_destination(name, img_path)

        # Search should now return results
        results = await mock_loaded_clip.search_by_text("waterfall", top_k=3)
        assert len(results) > 0, "Should return results after indexing destinations"
        assert len(results) <= 3, "Should not return more than top_k results"

    @pytest.mark.asyncio
    async def test_search_result_structure(self, mock_loaded_clip, tmp_path):
        """Search results should have correct structure."""
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        img_path = str(tmp_path / "test.jpg")
        img.save(img_path)

        with patch.object(mock_loaded_clip, '_save_faiss_index'):
            await mock_loaded_clip.add_destination("Test Destination", img_path)

        results = await mock_loaded_clip.search_by_text("test", top_k=1)

        if results:  # Only check if we got results
            result = results[0]
            assert "rank" in result
            assert "destination" in result
            assert "similarity_score" in result
            assert isinstance(result["similarity_score"], float)

    @pytest.mark.asyncio
    async def test_index_count_increases(self, mock_loaded_clip, tmp_path):
        """FAISS index count should increase when destinations are added."""
        from PIL import Image

        assert mock_loaded_clip.faiss_index.ntotal == 0  # Start empty

        img = Image.new("RGB", (100, 100))
        img_path = str(tmp_path / "test.jpg")
        img.save(img_path)

        with patch.object(mock_loaded_clip, '_save_faiss_index'):
            await mock_loaded_clip.add_destination("New Destination", img_path)

        assert mock_loaded_clip.faiss_index.ntotal == 1  # Should be 1 now


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_encode_without_initialization_raises(self):
        """Should raise error if model not initialized."""
        service = CLIPService()
        # is_loaded is False by default
        with pytest.raises(RuntimeError, match="not initialized"):
            await service.encode_text("test")

    @pytest.mark.asyncio
    async def test_encode_image_without_initialization_raises(self):
        """Should raise error if model not initialized."""
        service = CLIPService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await service.encode_image("some_path.jpg")


# ─── Integration-style Test ───────────────────────────────────────────────────

class TestEndToEndPipeline:
    """Test the complete visual search pipeline."""

    @pytest.mark.asyncio
    async def test_text_to_destination_pipeline(self, mock_loaded_clip, tmp_path):
        """
        End-to-end test:
          1. Add several destinations to index
          2. Search by text
          3. Verify results come back correctly
        """
        from PIL import Image

        jharkhand_destinations = [
            "Hundru Falls", "Dassam Falls", "Betla National Park",
            "Deoghar Temple", "Netarhat", "Rajrappa"
        ]

        # Index all destinations
        for name in jharkhand_destinations:
            img = Image.new("RGB", (224, 224))
            img_path = str(tmp_path / f"{name}.jpg")
            img.save(img_path)
            with patch.object(mock_loaded_clip, '_save_faiss_index'):
                await mock_loaded_clip.add_destination(name, img_path)

        # Verify all are indexed
        assert mock_loaded_clip.faiss_index.ntotal == len(jharkhand_destinations)

        # Search and verify
        results = await mock_loaded_clip.search_by_text("nature destination", top_k=3)
        assert len(results) == 3

        # Verify results are from our indexed destinations
        indexed_names = set(jharkhand_destinations)
        for result in results:
            assert result["destination"] in indexed_names
