"""
CLIP Service — Core Visual Search Engine
=========================================
What this file does:
  1. Loads OpenAI CLIP model (ViT-B/32) — downloads ~350MB on first run
  2. Encodes destination IMAGES into 512-dim vectors
  3. Encodes TEXT queries into the same 512-dim vector space
  4. Uses FAISS to find the most similar destinations

How CLIP works (simple explanation):
  - CLIP understands BOTH images and text in the same "language"
  - Image of a waterfall → [0.2, 0.8, 0.1, ...] (512 numbers)
  - Text "show me waterfalls" → [0.19, 0.79, 0.12, ...] (very similar numbers!)
  - FAISS finds the closest matches instantly

Flow:
  Tourist uploads photo → CLIP encodes it → FAISS searches → Returns similar destinations
  Tourist types query   → CLIP encodes it → FAISS searches → Returns matching destinations
"""

import os
import numpy as np
import torch
import faiss
import pickle
from PIL import Image
from pathlib import Path
import logging
import asyncio

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
MODEL_NAME = "ViT-B/32"                        # CLIP model variant (smaller = faster)
MODEL_CACHE_DIR = "./models/clip"              # Where to save downloaded model
FAISS_INDEX_PATH = "./models/faiss_index.bin"  # Saved FAISS index
EMBEDDING_DIM = 512                            # CLIP ViT-B/32 output size


class CLIPService:
    """
    Handles all image-text matching using OpenAI CLIP.
    
    Usage:
        service = CLIPService()
        await service.initialize()                    # Load model
        
        # Encode an image
        vector = await service.encode_image("waterfall.jpg")
        
        # Search by text
        results = await service.search_by_text("ancient temples in Jharkhand")
        
        # Search by image (visual search)
        results = await service.search_by_image("my_photo.jpg")
    """

    def __init__(self):
        self.model = None
        self.preprocess = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False

        # FAISS index stores all destination embeddings for fast search
        self.faiss_index = None

        # Maps FAISS index position → destination name
        # Example: {0: "Hundru Falls", 1: "Betla National Park", ...}
        self.index_to_destination = {}

    async def initialize(self):
        """
        Load CLIP model. Downloads automatically on first run (~350MB).
        Subsequent runs load from ./models/clip/ (instant).
        """
        try:
            import clip  # pip install openai-clip
            
            logger.info(f"Loading CLIP model '{MODEL_NAME}' on {self.device}...")
            
            # clip.load() downloads model if not cached, else loads from disk
            self.model, self.preprocess = clip.load(
                MODEL_NAME,
                device=self.device,
                download_root=MODEL_CACHE_DIR,  # Save to ai_ml/models/clip/
            )

            # Load existing FAISS index if available
            if os.path.exists(FAISS_INDEX_PATH):
                self._load_faiss_index()
                logger.info(f"FAISS index loaded with {self.faiss_index.ntotal} destinations")
            else:
                # Create empty FAISS index (will be populated when destinations are added)
                self._create_empty_faiss_index()
                logger.info("Created new empty FAISS index")

            self.is_loaded = True
            logger.info("✅ CLIP model ready!")

        except ImportError:
            logger.error("❌ 'clip' package not installed. Run: pip install openai-clip")
        except Exception as e:
            logger.error(f"❌ Failed to load CLIP: {e}")

    # ─── ENCODING FUNCTIONS ──────────────────────────────────────────────────

    async def encode_image(self, image_path: str) -> np.ndarray:
        """
        Convert an image file into a 512-dimensional vector.
        
        Step-by-step:
          1. Open image with PIL
          2. Preprocess: resize, normalize (CLIP expects 224x224 images)
          3. Pass through CLIP vision encoder (ViT transformer)
          4. Get 512-dim output vector
          5. Normalize to unit length (important for cosine similarity!)
        
        Args:
            image_path: Path to image file (jpg, png, etc.)
        
        Returns:
            numpy array of shape (512,) — the image's "fingerprint"
        """
        if not self.is_loaded:
            raise RuntimeError("CLIP model not initialized. Call initialize() first.")

        # Load and preprocess image
        image = Image.open(image_path).convert("RGB")
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        # Shape after preprocess: (1, 3, 224, 224) — batch of 1 image

        # Encode with CLIP (no gradient needed — we're just doing inference)
        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            # Shape: (1, 512)

        # Normalize to unit vector (needed for cosine similarity in FAISS)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        # Convert to numpy and return as 1D array
        return image_features.cpu().numpy().flatten()  # Shape: (512,)

    async def encode_text(self, text: str) -> np.ndarray:
        """
        Convert a text query into a 512-dimensional vector.
        
        CLIP maps text into the SAME space as images, so:
          encode_text("waterfall") ≈ encode_image("hundru_falls.jpg")
        
        Args:
            text: Any descriptive text (English, Hindi supported)
        
        Returns:
            numpy array of shape (512,) — the text's "fingerprint"
        """
        if not self.is_loaded:
            raise RuntimeError("CLIP model not initialized.")

        import clip

        # Tokenize text (converts words to numbers CLIP understands)
        text_tokens = clip.tokenize([text]).to(self.device)
        # Shape: (1, 77) — CLIP uses max 77 tokens

        with torch.no_grad():
            text_features = self.model.encode_text(text_tokens)
            # Shape: (1, 512)

        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return text_features.cpu().numpy().flatten()  # Shape: (512,)

    # ─── SEARCH FUNCTIONS ────────────────────────────────────────────────────

    async def search_by_text(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Find destinations matching a text description.
        
        Example:
            results = await search_by_text("tribal village with traditional dance", top_k=3)
            # Returns: [{"destination": "Sarhul Festival Area", "score": 0.89}, ...]
        
        How it works:
          1. Convert query text → 512-dim vector
          2. FAISS searches all destination vectors for closest matches
          3. Return top_k most similar destinations with similarity scores
        """
        query_vector = await self.encode_text(query)
        return self._faiss_search(query_vector, top_k)

    async def search_by_image(self, image_path: str, top_k: int = 5) -> list[dict]:
        """
        Find destinations visually similar to an uploaded photo.
        
        Example: Tourist uploads photo of a waterfall →
            Results: ["Hundru Falls", "Dassam Falls", "Jonha Falls"]
        
        How it works:
          1. Encode uploaded image → 512-dim vector
          2. FAISS searches all destination vectors for closest matches
          3. Return top_k most similar destinations
        """
        query_vector = await self.encode_image(image_path)
        return self._faiss_search(query_vector, top_k)

    def _faiss_search(self, query_vector: np.ndarray, top_k: int) -> list[dict]:
        """
        Internal FAISS search function.
        
        FAISS (Facebook AI Similarity Search) can search millions of vectors
        in milliseconds using optimized algorithms.
        
        Args:
            query_vector: 512-dim numpy array to search for
            top_k: How many results to return
        
        Returns:
            List of dicts: [{"destination": "name", "score": 0.95}, ...]
        """
        if self.faiss_index.ntotal == 0:
            return []  # No destinations indexed yet

        # Reshape for FAISS: needs (n_queries, embedding_dim)
        query_vector = query_vector.reshape(1, -1).astype(np.float32)

        # Search! Returns (distances, indices) — both shape (1, top_k)
        distances, indices = self.faiss_index.search(query_vector, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # -1 means FAISS found fewer results than top_k
                continue
            destination_name = self.index_to_destination.get(idx, f"Unknown_{idx}")
            results.append({
                "rank": i + 1,
                "destination": destination_name,
                "similarity_score": float(dist),  # Higher = more similar (cosine sim)
            })

        return results

    # ─── INDEX MANAGEMENT ────────────────────────────────────────────────────

    async def add_destination(self, destination_name: str, image_path: str):
        """
        Add a new destination to the FAISS index.
        Call this when a new destination is added to the platform.
        
        Example:
            await clip_service.add_destination("Hundru Falls", "./images/hundru.jpg")
        """
        vector = await self.encode_image(image_path)

        # FAISS index position = current total items
        idx = self.faiss_index.ntotal

        # Add vector to FAISS (shape must be (1, 512))
        self.faiss_index.add(vector.reshape(1, -1).astype(np.float32))

        # Remember which position = which destination
        self.index_to_destination[idx] = destination_name

        # Save updated index to disk
        self._save_faiss_index()

        logger.info(f"Added '{destination_name}' to FAISS index (total: {self.faiss_index.ntotal})")

    def _create_empty_faiss_index(self):
        """
        Create a new FAISS index using Inner Product (= cosine similarity
        when vectors are normalized, which we do in encode_image/encode_text).
        """
        self.faiss_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        # IndexFlatIP = Flat Index, Inner Product similarity
        # "Flat" = exact search (no approximation), fine for <100k destinations

    def _save_faiss_index(self):
        """Save FAISS index and destination mapping to disk."""
        faiss.write_index(self.faiss_index, FAISS_INDEX_PATH)
        with open(FAISS_INDEX_PATH + ".mapping.pkl", "wb") as f:
            pickle.dump(self.index_to_destination, f)

    def _load_faiss_index(self):
        """Load existing FAISS index from disk."""
        self.faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        mapping_path = FAISS_INDEX_PATH + ".mapping.pkl"
        if os.path.exists(mapping_path):
            with open(mapping_path, "rb") as f:
                self.index_to_destination = pickle.load(f)
