"""Analytics router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get analytics")
async def get_analytics():
    return {"message": "Analytics endpoint - to be implemented"}