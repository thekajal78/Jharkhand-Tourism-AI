"""
User models for the Jharkhand Tourism AI Platform.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for authentication and profile management."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Profile information
    preferences = Column(JSON, default={})  # User travel preferences
    location = Column(String(255), nullable=True)
    language_preference = Column(String(10), default="en")
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)


class UserProfile(Base):
    """Extended user profile for tourism preferences."""
    
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)
    
    # Travel preferences
    preferred_destination_types = Column(JSON, default=[])  # ["wildlife", "historical", etc.]
    budget_range = Column(String(50), nullable=True)  # "low", "medium", "high"
    travel_style = Column(String(50), nullable=True)  # "adventure", "leisure", "cultural"
    group_size_preference = Column(String(50), nullable=True)
    
    # Personal details
    age_group = Column(String(20), nullable=True)
    interests = Column(JSON, default=[])  # List of interests
    accessibility_needs = Column(JSON, default=[])
    
    # Analytics data
    total_trips = Column(Integer, default=0)
    favorite_destinations = Column(JSON, default=[])
    average_rating = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())