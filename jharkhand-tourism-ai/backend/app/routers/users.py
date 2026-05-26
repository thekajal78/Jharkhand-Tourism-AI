"""User management router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get users")
async def get_users():
    return {"message": "Users endpoint - to be implemented"}