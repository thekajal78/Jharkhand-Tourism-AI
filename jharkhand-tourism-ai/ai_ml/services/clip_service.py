"""
CLIP-based visual search service for Jharkhand Tourism AI Platform.
Provides image-text matching, visual similarity search, and geo-tagging capabilities.
"""

import os
import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import numpy as np
import torch
from PIL import Image
import clip
import cv2
from sklearn.metrics.pairwise import cosine_similarity
import faiss
import redis.asyncio as aioredis
import json
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class CLIPService:
    """
    CLIP-based visual search service for tourism applications.
    
    Features:
    - Image-text matching for destination queries
    - Visual similarity search
    - Geo-tagged image processing
    - Real-time visual recommendations
    """
    
    def __init__(self, model_name: str = "ViT-B/32", device: str = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        
        # Vector database for similarity search
        self.index = None
        self.image_metadata = {}
        
        # Redis for caching
        self.redis_client = None
        
        logger.info(f"Initializing CLIP service with model: {model_name} on device: {self.device}")
    
    async def initialize(self):
        """Initialize the CLIP model and supporting services."""
        try:
            # Load CLIP model
            self.model, self.preprocess = clip.load(self.model_name, device=self.device)
            self.model.eval()
            
            # Initialize Redis connection
            self.redis_client = await aioredis.from_url("redis://localhost:6379/1")
            
            # Initialize FAISS index for similarity search
            self._initialize_vector_index()
            
            logger.info("CLIP service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CLIP service: {e}")
            raise
    
    def _initialize_vector_index(self):
        """Initialize FAISS vector index for similarity search."""
        # CLIP ViT-B/32 produces 512-dimensional embeddings
        dimension = 512
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        logger.info(f"Initialized FAISS index with dimension: {dimension}")
    
    async def encode_image(self, image_path: str) -> np.ndarray:
        """
        Encode an image using CLIP model.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Image embedding as numpy array
        """
        try:
            # Check cache first
            image_hash = self._get_image_hash(image_path)
            cached_embedding = await self._get_cached_embedding(f"img_{image_hash}")
            
            if cached_embedding is not None:
                return cached_embedding
            
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                
            embedding = image_features.cpu().numpy().flatten()
            
            # Cache the embedding
            await self._cache_embedding(f"img_{image_hash}", embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text using CLIP model.
        
        Args:
            text: Input text query
            
        Returns:
            Text embedding as numpy array
        """
        try:
            # Check cache first
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cached_embedding = await self._get_cached_embedding(f"txt_{text_hash}")
            
            if cached_embedding is not None:
                return cached_embedding
            
            # Tokenize and encode text
            text_input = clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.encode_text(text_input)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            
            embedding = text_features.cpu().numpy().flatten()
            
            # Cache the embedding
            await self._cache_embedding(f"txt_{text_hash}", embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to encode text '{text}': {e}")
            raise
    
    async def find_similar_images(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 10
    ) -> List[Dict]:
        """
        Find similar images using vector similarity search.
        
        Args:
            query_embedding: Query image/text embedding
            top_k: Number of similar images to return
            
        Returns:
            List of similar images with metadata and scores
        """
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector index is empty")
                return []
            
            # Normalize query embedding
            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)
            
            # Search for similar vectors
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0:  # Valid index
                    metadata = self.image_metadata.get(idx, {})
                    results.append({
                        'image_id': metadata.get('image_id'),
                        'image_path': metadata.get('image_path'),
                        'location': metadata.get('location'),
                        'description': metadata.get('description'),
                        'similarity_score': float(score),
                        'geo_coordinates': metadata.get('geo_coordinates'),
                        'tags': metadata.get('tags', [])
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar images: {e}")
            return []
    
    async def visual_search_by_image(
        self, 
        query_image_path: str, 
        top_k: int = 10
    ) -> List[Dict]:
        """
        Perform visual search using an image query.
        
        Args:
            query_image_path: Path to query image
            top_k: Number of results to return
            
        Returns:
            List of similar destinations/images
        """
        try:
            # Encode query image
            query_embedding = await self.encode_image(query_image_path)
            
            # Find similar images
            similar_images = await self.find_similar_images(query_embedding, top_k)
            
            logger.info(f"Visual search returned {len(similar_images)} results for image: {query_image_path}")
            return similar_images
            
        except Exception as e:
            logger.error(f"Visual search failed for image {query_image_path}: {e}")
            return []
    
    async def visual_search_by_text(
        self, 
        query_text: str, 
        top_k: int = 10
    ) -> List[Dict]:
        """
        Perform visual search using a text query.
        
        Args:
            query_text: Text description query
            top_k: Number of results to return
            
        Returns:
            List of matching destinations/images
        """
        try:
            # Encode query text
            query_embedding = await self.encode_text(query_text)
            
            # Find similar images
            similar_images = await self.find_similar_images(query_embedding, top_k)
            
            logger.info(f"Text-based visual search returned {len(similar_images)} results for query: '{query_text}'")
            return similar_images
            
        except Exception as e:
            logger.error(f"Text-based visual search failed for query '{query_text}': {e}")
            return []
    
    async def add_image_to_index(
        self, 
        image_path: str, 
        metadata: Dict
    ) -> bool:
        """
        Add an image to the searchable index.
        
        Args:
            image_path: Path to the image file
            metadata: Image metadata including location, description, etc.
            
        Returns:
            Success status
        """
        try:
            # Generate embedding for the image
            embedding = await self.encode_image(image_path)
            
            # Normalize embedding for cosine similarity
            embedding_normalized = embedding.reshape(1, -1)
            faiss.normalize_L2(embedding_normalized)
            
            # Add to FAISS index
            current_index = self.index.ntotal
            self.index.add(embedding_normalized)
            
            # Store metadata
            self.image_metadata[current_index] = {
                'image_id': metadata.get('image_id', f"img_{current_index}"),
                'image_path': image_path,
                'location': metadata.get('location'),
                'description': metadata.get('description'),
                'geo_coordinates': metadata.get('geo_coordinates'),
                'tags': metadata.get('tags', []),
                'added_at': datetime.now().isoformat()
            }
            
            logger.info(f"Added image to index: {image_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add image to index {image_path}: {e}")
            return False
    
    async def process_geo_tagged_images(self, image_directory: str) -> Dict:
        """
        Process a directory of geo-tagged images for the tourism database.
        
        Args:
            image_directory: Directory containing tourism images
            
        Returns:
            Processing summary
        """
        try:
            image_dir = Path(image_directory)
            if not image_dir.exists():
                raise FileNotFoundError(f"Image directory not found: {image_directory}")
            
            processed_count = 0
            failed_count = 0
            
            # Supported image extensions
            supported_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}
            
            for image_file in image_dir.rglob('*'):
                if image_file.suffix.lower() in supported_extensions:
                    try:
                        # Extract metadata from filename/path (simplified approach)
                        metadata = self._extract_image_metadata(str(image_file))
                        
                        # Add to searchable index
                        success = await self.add_image_to_index(str(image_file), metadata)
                        
                        if success:
                            processed_count += 1
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to process image {image_file}: {e}")
                        failed_count += 1
            
            summary = {
                'total_processed': processed_count,
                'total_failed': failed_count,
                'index_size': self.index.ntotal if self.index else 0
            }
            
            logger.info(f"Geo-tagged image processing complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Geo-tagged image processing failed: {e}")
            return {'error': str(e)}
    
    def _extract_image_metadata(self, image_path: str) -> Dict:
        """
        Extract metadata from image file (simplified implementation).
        In production, this would use EXIF data and external geocoding services.
        """
        path_parts = Path(image_path).parts
        
        # Simple heuristic based on path structure
        metadata = {
            'image_id': Path(image_path).stem,
            'location': path_parts[-2] if len(path_parts) > 1 else 'Unknown',
            'description': f"Tourism image from {path_parts[-2] if len(path_parts) > 1 else 'Jharkhand'}",
            'tags': ['tourism', 'jharkhand'],
            'geo_coordinates': None  # Would be extracted from EXIF in production
        }
        
        return metadata
    
    def _get_image_hash(self, image_path: str) -> str:
        """Generate hash for image caching."""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    async def _get_cached_embedding(self, cache_key: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding from Redis."""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return np.frombuffer(cached_data, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Cache retrieval failed for {cache_key}: {e}")
        return None
    
    async def _cache_embedding(self, cache_key: str, embedding: np.ndarray):
        """Cache embedding to Redis."""
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key, 
                    3600,  # 1 hour TTL
                    embedding.astype(np.float32).tobytes()
                )
        except Exception as e:
            logger.warning(f"Cache storage failed for {cache_key}: {e}")
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            logger.info("CLIP service cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# FastAPI service endpoints
async def create_clip_service() -> CLIPService:
    """Create and initialize CLIP service instance."""
    service = CLIPService()
    await service.initialize()
    return service


if __name__ == "__main__":
    # Test the CLIP service
    async def test_clip_service():
        service = CLIPService()
        await service.initialize()
        
        # Test text encoding
        text_embedding = await service.encode_text("beautiful waterfall in Jharkhand")
        print(f"Text embedding shape: {text_embedding.shape}")
        
        await service.cleanup()
    
    asyncio.run(test_clip_service())