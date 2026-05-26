"""Analytics models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer

class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True)