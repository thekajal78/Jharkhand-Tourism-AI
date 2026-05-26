"""
Machine Learning Recommendation System for Jharkhand Tourism AI Platform.
Provides personalized recommendations using collaborative filtering and content-based approaches.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
import joblib
from datetime import datetime, timedelta
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    ML-powered recommendation system for tourism destinations.
    
    Features:
    - Collaborative filtering for user-based recommendations
    - Content-based filtering for destination similarities
    - Clustering analysis for user segmentation
    - Demand forecasting for popular destinations
    """
    
    def __init__(self):
        self.user_item_matrix = None
        self.destination_features = None
        self.user_clusters = None
        self.tfidf_vectorizer = None
        self.content_similarity_matrix = None
        self.redis_client = None
        
    async def initialize(self):
        """Initialize the recommendation service."""
        try:
            # Initialize Redis connection
            self.redis_client = await aioredis.from_url("redis://localhost:6379/2")
            
            # Load or initialize models
            await self._load_models()
            
            logger.info("Recommendation service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recommendation service: {e}")
            raise
    
    async def _load_models(self):
        """Load pre-trained models or initialize new ones."""
        try:
            # Try to load existing models
            self.user_item_matrix = await self._load_user_item_matrix()
            self.destination_features = await self._load_destination_features()
            
            if self.destination_features is not None:
                self._build_content_similarity_matrix()
            
        except Exception as e:
            logger.warning(f"Could not load existing models: {e}")
            # Initialize with dummy data for development
            self._initialize_dummy_data()
    
    def _initialize_dummy_data(self):
        """Initialize with dummy data for development."""
        # Create sample destination data
        destinations = [
            {'id': 1, 'name': 'Netarhat', 'type': 'Hill Station', 'features': 'scenic hills sunrise sunset'},
            {'id': 2, 'name': 'Betla National Park', 'type': 'Wildlife', 'features': 'tigers elephants forest safari'},
            {'id': 3, 'name': 'Hundru Falls', 'type': 'Waterfall', 'features': 'waterfall nature photography'},
            {'id': 4, 'name': 'Rock Garden Ranchi', 'type': 'Garden', 'features': 'rocks garden sculptures art'},
            {'id': 5, 'name': 'Palamau Fort', 'type': 'Historical', 'features': 'fort history architecture ancient'},
        ]
        
        self.destination_features = pd.DataFrame(destinations)
        self._build_content_similarity_matrix()
        
        logger.info("Initialized with dummy destination data")
    
    def _build_content_similarity_matrix(self):
        """Build content-based similarity matrix for destinations."""
        try:
            if self.destination_features is None or self.destination_features.empty:
                return
            
            # Create TF-IDF matrix from destination features
            feature_texts = self.destination_features['features'].fillna('')
            
            self.tfidf_vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(feature_texts)
            self.content_similarity_matrix = cosine_similarity(tfidf_matrix)
            
            logger.info(f"Built content similarity matrix: {self.content_similarity_matrix.shape}")
            
        except Exception as e:
            logger.error(f"Failed to build content similarity matrix: {e}")
    
    async def get_personalized_recommendations(
        self, 
        user_id: int, 
        num_recommendations: int = 10
    ) -> List[Dict]:
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id: User identifier
            num_recommendations: Number of recommendations to return
            
        Returns:
            List of recommended destinations with scores
        """
        try:
            # Check cache first
            cache_key = f"recommendations:{user_id}:{num_recommendations}"
            cached_recommendations = await self._get_cached_recommendations(cache_key)
            
            if cached_recommendations:
                return cached_recommendations
            
            # Get user preferences and history
            user_preferences = await self._get_user_preferences(user_id)
            user_history = await self._get_user_history(user_id)
            
            # Generate recommendations using hybrid approach
            recommendations = []
            
            # Content-based recommendations
            content_recs = self._get_content_based_recommendations(
                user_preferences, 
                user_history,
                num_recommendations // 2
            )
            recommendations.extend(content_recs)
            
            # Collaborative filtering recommendations
            collab_recs = await self._get_collaborative_recommendations(
                user_id,
                num_recommendations // 2
            )
            recommendations.extend(collab_recs)
            
            # Remove duplicates and sort by score
            seen_ids = set()
            unique_recommendations = []
            
            for rec in sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True):
                if rec['destination_id'] not in seen_ids:
                    unique_recommendations.append(rec)
                    seen_ids.add(rec['destination_id'])
                    
                if len(unique_recommendations) >= num_recommendations:
                    break
            
            # Cache recommendations
            await self._cache_recommendations(cache_key, unique_recommendations)
            
            logger.info(f"Generated {len(unique_recommendations)} recommendations for user {user_id}")
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
            return []
    
    def _get_content_based_recommendations(
        self, 
        user_preferences: Dict, 
        user_history: List[int],
        num_recommendations: int
    ) -> List[Dict]:
        """Generate content-based recommendations."""
        try:
            if self.content_similarity_matrix is None or self.destination_features is None:
                return []
            
            recommendations = []
            
            # If user has history, find similar destinations
            if user_history:
                for destination_id in user_history[-3:]:  # Use last 3 visited places
                    try:
                        # Find destination index
                        dest_idx = self.destination_features[
                            self.destination_features['id'] == destination_id
                        ].index
                        
                        if len(dest_idx) > 0:
                            idx = dest_idx[0]
                            similarities = self.content_similarity_matrix[idx]
                            
                            # Get most similar destinations
                            similar_indices = similarities.argsort()[-num_recommendations-1:-1][::-1]
                            
                            for sim_idx in similar_indices:
                                dest_row = self.destination_features.iloc[sim_idx]
                                if dest_row['id'] not in user_history:  # Don't recommend visited places
                                    recommendations.append({
                                        'destination_id': dest_row['id'],
                                        'destination_name': dest_row['name'],
                                        'destination_type': dest_row['type'],
                                        'score': float(similarities[sim_idx]),
                                        'reason': f"Similar to {self.destination_features.iloc[idx]['name']}"
                                    })
                    except Exception as e:
                        logger.warning(f"Error processing destination {destination_id}: {e}")
                        continue
            
            # If no history or need more recommendations, use preferences
            if len(recommendations) < num_recommendations and user_preferences:
                preferred_type = user_preferences.get('preferred_destination_type', '')
                if preferred_type:
                    type_matches = self.destination_features[
                        self.destination_features['type'].str.contains(preferred_type, case=False, na=False)
                    ]
                    
                    for _, dest_row in type_matches.head(num_recommendations).iterrows():
                        if dest_row['id'] not in [r['destination_id'] for r in recommendations]:
                            recommendations.append({
                                'destination_id': dest_row['id'],
                                'destination_name': dest_row['name'],
                                'destination_type': dest_row['type'],
                                'score': 0.7,
                                'reason': f"Matches your preference for {preferred_type}"
                            })
            
            return recommendations[:num_recommendations]
            
        except Exception as e:
            logger.error(f"Content-based recommendation failed: {e}")
            return []
    
    async def _get_collaborative_recommendations(
        self, 
        user_id: int,
        num_recommendations: int
    ) -> List[Dict]:
        """Generate collaborative filtering recommendations."""
        try:
            # Simplified collaborative filtering (would be more sophisticated in production)
            # Find similar users based on preferences and history
            similar_users = await self._find_similar_users(user_id)
            
            recommendations = []
            user_history = await self._get_user_history(user_id)
            
            for similar_user_id, similarity_score in similar_users[:5]:  # Top 5 similar users
                similar_user_history = await self._get_user_history(similar_user_id)
                
                # Recommend destinations that similar users visited but current user hasn't
                for dest_id in similar_user_history:
                    if dest_id not in user_history:
                        # Get destination details
                        dest_info = self.destination_features[
                            self.destination_features['id'] == dest_id
                        ]
                        
                        if not dest_info.empty:
                            dest_row = dest_info.iloc[0]
                            recommendations.append({
                                'destination_id': dest_row['id'],
                                'destination_name': dest_row['name'],
                                'destination_type': dest_row['type'],
                                'score': float(similarity_score * 0.8),  # Weight by user similarity
                                'reason': f"Popular among similar users"
                            })
                            
                            if len(recommendations) >= num_recommendations:
                                break
                
                if len(recommendations) >= num_recommendations:
                    break
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Collaborative filtering failed: {e}")
            return []
    
    async def get_trending_destinations(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get trending destinations based on recent activity."""
        try:
            # This would query actual booking/visit data in production
            # For now, return mock trending data
            trending = [
                {'destination_id': 1, 'name': 'Netarhat', 'trend_score': 0.95, 'visits_change': '+25%'},
                {'destination_id': 2, 'name': 'Betla National Park', 'trend_score': 0.88, 'visits_change': '+18%'},
                {'destination_id': 3, 'name': 'Hundru Falls', 'trend_score': 0.82, 'visits_change': '+15%'},
            ]
            
            return trending[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get trending destinations: {e}")
            return []
    
    async def analyze_user_segments(self) -> Dict:
        """Analyze user segments using clustering."""
        try:
            # This would use actual user data for clustering
            # Mock segmentation analysis
            segments = {
                'adventure_seekers': {'count': 150, 'preferences': ['Wildlife', 'Trekking', 'Waterfalls']},
                'culture_enthusiasts': {'count': 120, 'preferences': ['Historical', 'Temples', 'Museums']},
                'nature_lovers': {'count': 200, 'preferences': ['Hill Stations', 'Gardens', 'Scenic Views']},
                'family_tourists': {'count': 180, 'preferences': ['Safe destinations', 'Kid-friendly', 'Accessible']}
            }
            
            return segments
            
        except Exception as e:
            logger.error(f"User segmentation analysis failed: {e}")
            return {}
    
    async def forecast_demand(self, destination_id: int, days_ahead: int = 30) -> Dict:
        """Forecast demand for a destination."""
        try:
            # Mock demand forecasting (would use time series analysis in production)
            base_demand = np.random.randint(50, 200)
            seasonal_factor = 1 + 0.3 * np.sin(np.pi * datetime.now().month / 6)
            trend_factor = 1 + np.random.uniform(-0.1, 0.1)
            
            forecasted_demand = int(base_demand * seasonal_factor * trend_factor)
            
            return {
                'destination_id': destination_id,
                'forecasted_visitors': forecasted_demand,
                'confidence_level': 0.75,
                'peak_days': ['Saturday', 'Sunday'],
                'recommendation': 'High demand expected' if forecasted_demand > 150 else 'Moderate demand expected'
            }
            
        except Exception as e:
            logger.error(f"Demand forecasting failed for destination {destination_id}: {e}")
            return {}
    
    # Helper methods
    async def _get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences from database or cache."""
        # Mock user preferences
        return {
            'preferred_destination_type': 'Nature',
            'budget_range': 'medium',
            'travel_style': 'adventure'
        }
    
    async def _get_user_history(self, user_id: int) -> List[int]:
        """Get user's visit history."""
        # Mock user history
        return [1, 3] if user_id % 2 == 0 else [2, 4]
    
    async def _find_similar_users(self, user_id: int) -> List[Tuple[int, float]]:
        """Find users similar to the given user."""
        # Mock similar users
        return [(user_id + 1, 0.8), (user_id + 2, 0.7), (user_id + 3, 0.6)]
    
    async def _get_cached_recommendations(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached recommendations from Redis."""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    import json
                    return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_recommendations(self, cache_key: str, recommendations: List[Dict]):
        """Cache recommendations to Redis."""
        try:
            if self.redis_client:
                import json
                await self.redis_client.setex(
                    cache_key,
                    1800,  # 30 minutes TTL
                    json.dumps(recommendations, default=str)
                )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    async def _load_user_item_matrix(self):
        """Load user-item interaction matrix."""
        # Would load from file or database in production
        return None
    
    async def _load_destination_features(self):
        """Load destination features."""
        # Would load from file or database in production
        return None
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Recommendation service cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


if __name__ == "__main__":
    # Test the recommendation service
    async def test_recommendation_service():
        service = RecommendationService()
        await service.initialize()
        
        # Test personalized recommendations
        recommendations = await service.get_personalized_recommendations(user_id=1, num_recommendations=5)
        print(f"Recommendations: {recommendations}")
        
        # Test trending destinations
        trending = await service.get_trending_destinations()
        print(f"Trending destinations: {trending}")
        
        await service.cleanup()
    
    asyncio.run(test_recommendation_service())