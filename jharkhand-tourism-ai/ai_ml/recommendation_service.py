"""
Recommendation Service
=======================
What this file does:
  Suggests destinations/itineraries to tourists based on:
  - Their past preferences (what they liked before)
  - Similar users' behavior (collaborative filtering)
  - Destination features (content-based filtering)

Three algorithms inside:
  1. Content-Based Filtering  → "You liked waterfalls, here are more waterfalls"
  2. Collaborative Filtering  → "People like you also visited Netarhat"
  3. Hybrid Model             → Combines both for best results

Simple mental model:
  Netflix recommends shows based on what YOU watched + what similar users watched.
  We do the same for Jharkhand destinations.
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
MODEL_PATH = "./models/recommendation_model.pkl"


class RecommendationService:
    """
    Recommends Jharkhand destinations to tourists.

    Usage:
        service = RecommendationService()
        await service.initialize()

        # Get personalized recommendations for a user
        recs = await service.get_recommendations(user_id=42, top_k=5)

        # Get similar destinations to a given one
        similar = await service.get_similar_destinations("Hundru Falls", top_k=3)
    """

    def __init__(self):
        self.is_loaded = False

        # ── Data matrices ──────────────────────────────────────────────────
        # user_item_matrix: rows=users, cols=destinations, values=ratings(0-5)
        # Example:
        #          Hundru  Betla  Netarhat  Rajrappa
        # user_1      5      3       0         4
        # user_2      0      5       4         0
        self.user_item_matrix = None

        # destination_features: rows=destinations, cols=features (type, district, etc.)
        # Example:
        #              waterfall  wildlife  temple  tribal  eco
        # Hundru Falls     1        0        0       0      1
        # Betla NP         0        1        0       1      1
        self.destination_features = None

        # Similarity matrices (pre-computed for speed)
        self.user_similarity_matrix = None         # Which users are similar
        self.destination_similarity_matrix = None  # Which destinations are similar

        self.scaler = MinMaxScaler()

    async def initialize(self):
        """Load pre-trained model or build from scratch with sample data."""
        try:
            if Path(MODEL_PATH).exists():
                self._load_model()
                logger.info("✅ Recommendation model loaded from disk")
            else:
                logger.info("No saved model found — building with sample data...")
                self._build_sample_data()
                self._train()
                self._save_model()
                logger.info("✅ Recommendation model built and saved")

            self.is_loaded = True

        except Exception as e:
            logger.error(f"❌ Recommendation service failed: {e}")

    # ─── MAIN RECOMMENDATION FUNCTIONS ──────────────────────────────────────

    async def get_recommendations(self, user_id: int, top_k: int = 5) -> list[dict]:
        """
        Get personalized destination recommendations for a user.
        Uses hybrid approach: 60% collaborative + 40% content-based.

        Args:
            user_id: The user's ID from database
            top_k: How many recommendations to return

        Returns:
            [{"destination": "Hundru Falls", "score": 0.92, "reason": "..."}]
        """
        collab_scores = self._collaborative_filtering(user_id, top_k * 2)
        content_scores = self._content_based_filtering(user_id, top_k * 2)

        # Combine scores (hybrid model)
        hybrid_scores = {}
        for dest, score in collab_scores.items():
            hybrid_scores[dest] = score * 0.6  # 60% weight to collaborative

        for dest, score in content_scores.items():
            if dest in hybrid_scores:
                hybrid_scores[dest] += score * 0.4  # 40% weight to content-based
            else:
                hybrid_scores[dest] = score * 0.4

        # Sort and return top_k
        sorted_results = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "rank": i + 1,
                "destination": dest,
                "score": round(score, 3),
                "reason": self._generate_reason(dest, user_id),
            }
            for i, (dest, score) in enumerate(sorted_results[:top_k])
        ]

    async def get_similar_destinations(self, destination: str, top_k: int = 5) -> list[dict]:
        """
        Find destinations similar to a given one based on features.

        Example: get_similar_destinations("Hundru Falls")
        → ["Dassam Falls", "Jonha Falls", "Hirni Falls"]

        How: Uses cosine similarity on destination feature vectors
        """
        if destination not in self.destination_features.index:
            return []

        # Get similarity scores for this destination
        dest_idx = list(self.destination_features.index).index(destination)
        similarity_scores = self.destination_similarity_matrix[dest_idx]

        # Create (destination, score) pairs, exclude the destination itself
        results = []
        for i, (dest_name, score) in enumerate(
            zip(self.destination_features.index, similarity_scores)
        ):
            if dest_name != destination:
                results.append({"destination": dest_name, "similarity": round(float(score), 3)})

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    async def get_popular_destinations(self, top_k: int = 10) -> list[dict]:
        """
        Return most popular destinations based on overall ratings.
        Used for homepage / new users with no history.
        """
        if self.user_item_matrix is None:
            return []

        # Average rating per destination
        avg_ratings = self.user_item_matrix.mean(axis=0)
        # Number of ratings per destination (popularity)
        rating_counts = (self.user_item_matrix > 0).sum(axis=0)

        # Weighted score: average rating × log(count) (Bayesian average approach)
        popularity_scores = avg_ratings * np.log1p(rating_counts)
        popularity_scores = popularity_scores / popularity_scores.max()  # Normalize 0-1

        results = [
            {"destination": dest, "popularity_score": round(float(score), 3)}
            for dest, score in zip(self.user_item_matrix.columns, popularity_scores)
        ]
        results.sort(key=lambda x: x["popularity_score"], reverse=True)
        return results[:top_k]

    # ─── ALGORITHM IMPLEMENTATIONS ───────────────────────────────────────────

    def _collaborative_filtering(self, user_id: int, top_k: int) -> dict:
        """
        Collaborative Filtering: "People like you also visited X"

        Steps:
          1. Find users most similar to current user (using cosine similarity)
          2. Look at what those similar users rated highly
          3. Recommend destinations the current user hasn't visited yet

        Think of it like: your friends' recommendations
        """
        if self.user_item_matrix is None:
            return {}

        user_idx = user_id % len(self.user_item_matrix)  # Map user_id to matrix index

        # Get similarity scores with all other users
        user_similarities = self.user_similarity_matrix[user_idx]

        # Weighted sum of other users' ratings
        # (more similar users get higher weight)
        weighted_ratings = np.dot(user_similarities, self.user_item_matrix.values)
        # Shape: (n_destinations,)

        # Subtract already-visited destinations (rating > 0)
        already_visited = self.user_item_matrix.iloc[user_idx].values > 0
        weighted_ratings[already_visited] = 0  # Don't recommend visited places

        # Create destination → score mapping
        scores = {
            dest: float(score)
            for dest, score in zip(self.user_item_matrix.columns, weighted_ratings)
            if score > 0
        }

        return scores

    def _content_based_filtering(self, user_id: int, top_k: int) -> dict:
        """
        Content-Based Filtering: "You liked waterfalls, here are more waterfalls"

        Steps:
          1. Build a "user profile" from their past ratings
             (weighted average of destination feature vectors)
          2. Find destinations most similar to this profile
          3. Recommend top matches

        Think of it like: Spotify's "based on your taste" recommendations
        """
        if self.user_item_matrix is None or self.destination_features is None:
            return {}

        user_idx = user_id % len(self.user_item_matrix)
        user_ratings = self.user_item_matrix.iloc[user_idx].values
        # Shape: (n_destinations,)

        if user_ratings.sum() == 0:
            return {}  # New user, no history

        # Build user profile vector
        # Weighted average of destination features, weighted by ratings
        user_profile = np.dot(user_ratings, self.destination_features.values)
        # Shape: (n_features,)

        # Find similarity between user profile and all destinations
        user_profile = user_profile.reshape(1, -1)
        dest_features = self.destination_features.values

        similarities = cosine_similarity(user_profile, dest_features).flatten()
        # Shape: (n_destinations,)

        # Don't recommend already visited
        already_visited = user_ratings > 0
        similarities[already_visited] = 0

        scores = {
            dest: float(score)
            for dest, score in zip(self.destination_features.index, similarities)
            if score > 0
        }

        return scores

    # ─── TRAINING ────────────────────────────────────────────────────────────

    def _train(self):
        """
        Pre-compute similarity matrices.
        Called once during initialization.

        Why pre-compute? Computing cosine similarity at query time is slow.
        Pre-computing and caching makes recommendations instant.
        """
        logger.info("Computing similarity matrices...")

        # User-User similarity matrix
        # Shape: (n_users, n_users)
        self.user_similarity_matrix = cosine_similarity(self.user_item_matrix.values)

        # Destination-Destination similarity matrix
        # Shape: (n_destinations, n_destinations)
        self.destination_similarity_matrix = cosine_similarity(
            self.destination_features.values
        )

        logger.info("✅ Similarity matrices computed")

    def _build_sample_data(self):
        """
        Build sample data for Jharkhand destinations.
        In production, this comes from your PostgreSQL database.
        """
        # ── Destinations ──────────────────────────────────────────────────
        destinations = [
            "Hundru Falls", "Dassam Falls", "Jonha Falls", "Hirni Falls",
            "Betla National Park", "Dalma Wildlife Sanctuary",
            "Deoghar Temple", "Baidyanath Dham", "Rajrappa Temple",
            "Netarhat", "Parasnath Hill", "Panchghagh Falls",
            "Hazaribagh Lake", "Topchanchi Lake",
            "Tribal Village Khunti", "Sarhul Festival Ground",
        ]

        # ── Destination Features ───────────────────────────────────────────
        # Each destination described by features (1=has this feature, 0=doesn't)
        # Features: waterfall, wildlife, temple, tribal, eco, lake, hill, festival
        feature_data = {
            "waterfall": [1,1,1,1, 0,0, 0,0,0, 0,0,1, 0,0, 0,0],
            "wildlife":  [0,0,0,0, 1,1, 0,0,0, 0,0,0, 0,0, 0,0],
            "temple":    [0,0,0,0, 0,0, 1,1,1, 0,0,0, 0,0, 0,0],
            "tribal":    [0,0,0,0, 1,0, 0,0,0, 0,1,0, 0,0, 1,1],
            "eco":       [1,1,1,1, 1,1, 0,0,0, 1,1,1, 1,1, 1,0],
            "lake":      [0,0,0,0, 0,0, 0,0,0, 0,0,0, 1,1, 0,0],
            "hill":      [0,0,0,0, 0,0, 0,0,0, 1,1,0, 0,0, 0,0],
            "festival":  [0,0,0,0, 0,0, 1,1,1, 0,0,0, 0,0, 0,1],
        }

        self.destination_features = pd.DataFrame(
            feature_data, index=destinations
        )

        # ── User-Item Rating Matrix ────────────────────────────────────────
        # Simulated ratings (0=not visited, 1-5=rating)
        # In production: loaded from PostgreSQL bookings/reviews table
        np.random.seed(42)
        n_users = 50
        ratings = np.random.randint(0, 6, size=(n_users, len(destinations)))
        # Make it sparse (most users haven't visited most places)
        mask = np.random.random((n_users, len(destinations))) > 0.7
        ratings[mask] = 0

        self.user_item_matrix = pd.DataFrame(
            ratings, columns=destinations,
            index=[f"user_{i}" for i in range(n_users)]
        )

    def _generate_reason(self, destination: str, user_id: int) -> str:
        """Generate a human-readable reason for the recommendation."""
        reasons = {
            "waterfall": "Based on your interest in waterfalls",
            "wildlife":  "Based on your love for wildlife",
            "temple":    "Based on your interest in religious sites",
            "tribal":    "Based on your interest in tribal culture",
            "eco":       "Perfect for eco-tourism lovers like you",
        }

        if self.destination_features is not None and destination in self.destination_features.index:
            features = self.destination_features.loc[destination]
            for feature, reason in reasons.items():
                if features.get(feature, 0) == 1:
                    return reason

        return "Trending in Jharkhand"

    def _save_model(self):
        data = {
            "user_item_matrix": self.user_item_matrix,
            "destination_features": self.destination_features,
            "user_similarity_matrix": self.user_similarity_matrix,
            "destination_similarity_matrix": self.destination_similarity_matrix,
        }
        Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(data, f)

    def _load_model(self):
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        self.user_item_matrix = data["user_item_matrix"]
        self.destination_features = data["destination_features"]
        self.user_similarity_matrix = data["user_similarity_matrix"]
        self.destination_similarity_matrix = data["destination_similarity_matrix"]
