"""Database models for users and search history."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from passlib.context import CryptContext

# Password hashing using pbkdf2_sha256 (no bcrypt backend issues, no 72-byte cap)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class User(Base):
    """User model for authentication and search history."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    itineraries = relationship("Itinerary", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set password (bcrypt_sha256 handles long secrets)."""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, self.hashed_password)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class SearchHistory(Base):
    """Model for storing user search/query history."""
    
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Query details
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    user_type = Column(String(50), nullable=False)  # student, elderly, tourist, etc.
    group_size = Column(Integer, default=1)
    group_type = Column(String(50), default="solo")
    
    # Results
    query_text = Column(Text)  # Original voice/text query
    selected_option = Column(String(50))  # cheapest, fastest, door_to_door
    total_cost = Column(Integer)  # Cost in rupees
    duration = Column(Integer)  # Duration in minutes
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship back to user
    user = relationship("User", back_populates="searches")
    
    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, origin='{self.origin}' -> '{self.destination}')>"


class Itinerary(Base):
    """Model for storing tourist itineraries."""
    
    __tablename__ = "itineraries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Itinerary details
    title = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    days = Column(Integer, default=1)
    num_people = Column(Integer, default=1)
    
    # Itinerary content (stored as JSON string)
    itinerary_data = Column(Text, nullable=False)  # JSON with daily_plan, places, etc.
    interests = Column(String(500))  # Comma-separated interests
    budget = Column(String(50), default="moderate")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to user
    user = relationship("User", back_populates="itineraries")
    
    def __repr__(self):
        return f"<Itinerary(id={self.id}, user_id={self.user_id}, city='{self.city}', days={self.days})>"
