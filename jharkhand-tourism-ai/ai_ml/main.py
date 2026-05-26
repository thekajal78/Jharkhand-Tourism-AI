"""
Safar Sathi - AI/ML Service
Port: 8001
This is the main entry point for all AI/ML features.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from services.clip_service import CLIPService
from services.recommendation_service import RecommendationService
from services.chatbot_service import ChatbotService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Global service instances ───────────────────────────────────────────────
clip_service = CLIPService()
recommendation_service = RecommendationService()
chatbot_service = ChatbotService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all AI models when the server starts."""
    logger.info("🚀 Starting AI/ML Service...")

    logger.info("📦 Loading CLIP model...")
    await clip_service.initialize()

    logger.info("🤖 Loading Recommendation model...")
    await recommendation_service.initialize()

    logger.info("💬 Loading Chatbot model...")
    await chatbot_service.initialize()

    logger.info("✅ All AI models loaded successfully!")

    # Attach to app state so routers can access them
    app.state.clip = clip_service
    app.state.recommender = recommendation_service
    app.state.chatbot = chatbot_service

    yield  # Server is running here

    logger.info("🛑 Shutting down AI/ML Service...")


# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Safar Sathi - AI/ML Service",
    description="CLIP visual search, recommendations, and multilingual chatbot",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "models": {
            "clip": clip_service.is_loaded,
            "recommender": recommendation_service.is_loaded,
            "chatbot": chatbot_service.is_loaded,
        }
    }


# ─── Register Routers ────────────────────────────────────────────────────────
from routers import clip_router, recommendation_router, chatbot_router

app.include_router(clip_router.router, prefix="/clip",           tags=["CLIP Visual Search"])
app.include_router(recommendation_router.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(chatbot_router.router, prefix="/chat",        tags=["Chatbot"])
