"""Admin models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)