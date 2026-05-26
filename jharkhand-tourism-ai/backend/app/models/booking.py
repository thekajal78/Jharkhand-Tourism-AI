"""Booking models - placeholder"""
from app.database import Base
from sqlalchemy import Column, Integer, String

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)