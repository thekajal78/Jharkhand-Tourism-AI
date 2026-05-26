"""Images and CLIP router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Get images")
async def get_images():
    return {"message": "Images endpoint - to be implemented"}