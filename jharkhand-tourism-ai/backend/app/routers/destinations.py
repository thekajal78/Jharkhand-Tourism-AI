"""Destinations router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get destinations")
async def get_destinations():
    return {"message": "Destinations endpoint - to be implemented"}