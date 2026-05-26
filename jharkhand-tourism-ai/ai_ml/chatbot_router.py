"""
Chatbot API Router
===================
Endpoints:
  POST /chat/message           → Send a message, get AI response
  POST /chat/sentiment         → Analyze sentiment of a review
  GET  /chat/languages         → List supported languages
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: int
    message: str
    conversation_history: list = []   # Previous messages for context


class SentimentRequest(BaseModel):
    review_text: str


@router.post("/message")
async def chat(body: ChatRequest, request: Request):
    """
    Process tourist message and return AI response.

    Handles: English, Hindi, Santali (tribal), and more.

    Example request:
        {"user_id": 1, "message": "मुझे झरने दिखाओ", "conversation_history": []}

    Example response:
        {
          "intent": "find_destination",
          "response_text": "यहाँ झारखंड के सुंदर झरने हैं...",
          "detected_language": "hindi",
          "entities": {"locations": [], "duration_days": null},
          "suggestions": ["Show on Map", "Book Guide", "Get Itinerary"],
          "confidence": 0.9
        }
    """
    chatbot = request.app.state.chatbot
    if not chatbot.is_loaded:
        raise HTTPException(503, "Chatbot not loaded")

    response = await chatbot.process_message(
        user_id=body.user_id,
        message=body.message,
        conversation_history=body.conversation_history,
    )
    return response


@router.post("/sentiment")
async def analyze_sentiment(body: SentimentRequest, request: Request):
    """
    Analyze sentiment of a tourist review.
    Used by admin dashboard.

    Example:
        {"review_text": "Hundru Falls was absolutely stunning! Loved it."}
        → {"sentiment": "positive", "score": 0.92}
    """
    chatbot = request.app.state.chatbot
    result = await chatbot.analyze_sentiment(body.review_text)
    return result


@router.get("/languages")
def get_supported_languages():
    """Return list of supported languages."""
    return {
        "supported_languages": [
            {"code": "english", "name": "English", "script": "Latin"},
            {"code": "hindi",   "name": "हिंदी (Hindi)", "script": "Devanagari"},
            {"code": "santali", "name": "ᱥᱟᱱᱛᱟᱲᱤ (Santali)", "script": "Ol Chiki"},
            {"code": "ho",      "name": "Ho", "script": "Warang Citi"},
            {"code": "mundari", "name": "Mundari", "script": "Devanagari"},
        ]
    }
