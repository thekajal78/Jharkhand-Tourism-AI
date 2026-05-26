"""
Jharkhand Tourism AI Platform - FastAPI Backend
Main application entry point with routing and middleware configuration.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path

# Import routers
from app.routers import (
    auth,
    users,
    destinations,
    bookings,
    recommendations,
    images,
    chatbot,
    analytics,
    admin
)
from app.database import engine, Base
from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Jharkhand Tourism AI Platform...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize AI services
    try:
        from app.services.ai_service import AIService
        ai_service = AIService()
        await ai_service.initialize()
        app.state.ai_service = ai_service
        logger.info("AI services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI services: {e}")
    
    # Initialize CLIP service
    try:
        from app.services.clip_service import CLIPService
        clip_service = CLIPService()
        await clip_service.initialize()
        app.state.clip_service = clip_service
        logger.info("CLIP service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize CLIP service: {e}")
    
    logger.info("Application startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Jharkhand Tourism AI Platform...")
    
    # Cleanup AI services
    if hasattr(app.state, 'ai_service'):
        await app.state.ai_service.cleanup()
    
    if hasattr(app.state, 'clip_service'):
        await app.state.clip_service.cleanup()
    
    logger.info("Application shutdown complete!")


# Initialize FastAPI application
app = FastAPI(
    title="Jharkhand Tourism AI Platform",
    description="AI-powered tourism platform for Jharkhand state with CLIP image processing, ML recommendations, and real-time analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Mount static files
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": "2024-01-01T00:00:00Z"
    }


# API version endpoint
@app.get("/version", tags=["Info"])
async def get_version():
    """Get application version information."""
    return {
        "version": "1.0.0",
        "name": "Jharkhand Tourism AI Platform",
        "description": "AI-powered tourism platform with CLIP image processing",
        "features": [
            "CLIP-based visual search",
            "ML recommendation system",
            "Multilingual chatbot",
            "Real-time analytics",
            "Interactive maps"
        ]
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": "Welcome to Jharkhand Tourism AI Platform",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "version": "/version"
    }


# Include routers with API prefix
api_v1 = "/api/v1"

app.include_router(auth.router, prefix=f"{api_v1}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{api_v1}/users", tags=["Users"])
app.include_router(destinations.router, prefix=f"{api_v1}/destinations", tags=["Destinations"])
app.include_router(bookings.router, prefix=f"{api_v1}/bookings", tags=["Bookings"])
app.include_router(recommendations.router, prefix=f"{api_v1}/recommendations", tags=["Recommendations"])
app.include_router(images.router, prefix=f"{api_v1}/images", tags=["Images & CLIP"])
app.include_router(chatbot.router, prefix=f"{api_v1}/chatbot", tags=["Chatbot"])
app.include_router(analytics.router, prefix=f"{api_v1}/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix=f"{api_v1}/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )