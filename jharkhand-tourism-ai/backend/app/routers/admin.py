"""Admin router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get admin data")
async def get_admin():
    return {"message": "Admin endpoint - to be implemented"}