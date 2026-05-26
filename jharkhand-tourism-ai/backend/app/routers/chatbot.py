"""Chatbot router."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Chat with bot")
async def chat():
    return {"message": "Chatbot endpoint - to be implemented"}