"""
Destination models for tourism data.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Destination(Base):
    """Tourism destination model."""
    
    __tablename__ = "destinations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Location data
    state = Column(String(100), default="Jharkhand")
    district = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Classification
    category = Column(String(100), nullable=True)  # "wildlife", "historical", "natural", etc.
    subcategory = Column(String(100), nullable=True)
    difficulty_level = Column(String(20), nullable=True)  # "easy", "moderate", "difficult"
    
    # Visitor information
    entry_fee = Column(Float, default=0.0)
    visiting_hours = Column(String(100), nullable=True)
    best_time_to_visit = Column(String(100), nullable=True)
    estimated_duration = Column(String(50), nullable=True)  # "2-3 hours"
    
    # Features and amenities
    features = Column(JSON, default=[])  # List of features/keywords
    amenities = Column(JSON, default=[])  # Available amenities
    accessibility = Column(JSON, default={})  # Accessibility information
    
    # Media
    images = Column(JSON, default=[])  # Image URLs/paths
    videos = Column(JSON, default=[])  # Video URLs
    
    # Ratings and popularity
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    popularity_score = Column(Float, default=0.0)
    visitor_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DestinationImage(Base):
    """Images associated with destinations for CLIP processing."""
    
    __tablename__ = "destination_images"
    
    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)
    
    # Image data
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Image metadata
    alt_text = Column(String(255), nullable=True)
    caption = Column(Text, nullable=True)
    tags = Column(JSON, default=[])
    
    # CLIP embeddings
    clip_embedding = Column(JSON, nullable=True)  # Stored as JSON array
    embedding_version = Column(String(50), nullable=True)  # Model version used
    
    # Image properties
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String(10), nullable=True)  # jpg, png, etc.
    
    # Status
    is_primary = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)  # CLIP processed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DestinationReview(Base):
    """User reviews for destinations."""
    
    __tablename__ = "destination_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    
    # Review metadata
    visit_date = Column(DateTime, nullable=True)
    trip_type = Column(String(50), nullable=True)  # solo, family, couple, etc.
    
    # Sentiment analysis
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)  # positive, negative, neutral
    
    # Moderation
    is_verified = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())