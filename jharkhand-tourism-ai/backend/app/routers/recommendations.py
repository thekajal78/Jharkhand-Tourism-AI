"""Recommendations router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get recommendations")
async def get_recommendations():
    return {"message": "Recommendations endpoint - to be implemented"}