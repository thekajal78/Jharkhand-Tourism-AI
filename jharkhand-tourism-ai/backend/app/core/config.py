"""
Configuration settings for the Jharkhand Tourism AI Platform.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Jharkhand Tourism AI Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Security
    SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    # AI/ML Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    CLIP_MODEL_PATH: str = Field(default="./ai_ml/models/clip", env="CLIP_MODEL_PATH")
    ML_MODEL_PATH: str = Field(default="./ai_ml/models/recommendations", env="ML_MODEL_PATH")
    
    # File Upload
    UPLOAD_PATH: str = Field(default="./uploads", env="UPLOAD_PATH")
    MAX_FILE_SIZE: str = Field(default="50MB", env="MAX_FILE_SIZE")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "webp"],
        env="ALLOWED_EXTENSIONS"
    )
    
    # External APIs
    MAPS_API_KEY: Optional[str] = Field(default=None, env="MAPS_API_KEY")
    WEATHER_API_KEY: Optional[str] = Field(default=None, env="WEATHER_API_KEY")
    
    # Email Configuration
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@jharkhand-tourism.com", env="EMAIL_FROM")
    
    # Monitoring
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    MAX_PAGE_SIZE: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Cache TTL (in seconds)
    CACHE_TTL_SHORT: int = Field(default=300, env="CACHE_TTL_SHORT")  # 5 minutes
    CACHE_TTL_MEDIUM: int = Field(default=1800, env="CACHE_TTL_MEDIUM")  # 30 minutes
    CACHE_TTL_LONG: int = Field(default=3600, env="CACHE_TTL_LONG")  # 1 hour
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True) 
    def assemble_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
        
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def assemble_allowed_extensions(cls, v):
        """Parse allowed file extensions from string or list."""
        if isinstance(v, str):
            return [i.strip().lower() for i in v.split(",")]
        return v
    
    @validator("MAX_FILE_SIZE")
    def parse_max_file_size(cls, v):
        """Convert file size string to bytes."""
        if isinstance(v, str):
            size_map = {
                'KB': 1024,
                'MB': 1024 ** 2,
                'GB': 1024 ** 3
            }
            
            v = v.upper()
            for unit, multiplier in size_map.items():
                if v.endswith(unit):
                    return int(v.replace(unit, '')) * multiplier
            
            # Default to bytes if no unit specified
            return int(v)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()

# Create upload directory if it doesn't exist
Path(settings.UPLOAD_PATH).mkdir(parents=True, exist_ok=True)