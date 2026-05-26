"""Image models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True)