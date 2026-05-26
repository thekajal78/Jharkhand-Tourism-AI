"""Chat models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)