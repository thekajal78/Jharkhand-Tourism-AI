"""
Recommendation API Router
==========================
Endpoints:
  GET  /recommend/user/{user_id}        → Personalized recommendations for a user
  GET  /recommend/similar/{destination} → Find similar destinations
  GET  /recommend/popular               → Most popular destinations (for new users)
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/user/{user_id}")
async def get_user_recommendations(user_id: int, top_k: int = 5, request: Request = None):
    """
    Get personalized destination recommendations for a specific user.

    Uses hybrid model: 60% collaborative filtering + 40% content-based.

    Example response:
        [
          {"rank": 1, "destination": "Netarhat", "score": 0.92, "reason": "Based on your interest in hills"},
          {"rank": 2, "destination": "Hundru Falls", "score": 0.88, "reason": "Trending in Jharkhand"},
          ...
        ]
    """
    recommender = request.app.state.recommender
    if not recommender.is_loaded:
        raise HTTPException(503, "Recommendation model not loaded")

    results = await recommender.get_recommendations(user_id, top_k)
    return {"user_id": user_id, "recommendations": results}


@router.get("/similar/{destination}")
async def get_similar_destinations(destination: str, top_k: int = 5, request: Request = None):
    """
    Find destinations similar to a given one.

    Example:
        GET /recommend/similar/Hundru%20Falls
        → ["Dassam Falls", "Jonha Falls", "Hirni Falls"]
    """
    recommender = request.app.state.recommender
    if not recommender.is_loaded:
        raise HTTPException(503, "Recommendation model not loaded")

    results = await recommender.get_similar_destinations(destination, top_k)
    if not results:
        raise HTTPException(404, f"Destination '{destination}' not found in index")

    return {"destination": destination, "similar": results}


@router.get("/popular")
async def get_popular_destinations(top_k: int = 10, request: Request = None):
    """
    Get most popular destinations overall.
    Used for homepage and new users with no history.
    """
    recommender = request.app.state.recommender
    results = await recommender.get_popular_destinations(top_k)
    return {"popular_destinations": results}
