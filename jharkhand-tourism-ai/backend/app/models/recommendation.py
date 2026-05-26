"""Recommendation models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)