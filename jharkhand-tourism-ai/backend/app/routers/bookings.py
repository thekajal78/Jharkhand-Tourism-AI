"""Bookings router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get bookings")
async def get_bookings():
    return {"message": "Bookings endpoint - to be implemented"}