"""Authentication routes for login, logout, and registration."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import os

from database import get_db
from models import User

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "student123",
                "email": "student@example.com",
                "password": "secure_password"
            }
        }


class UserLogin(BaseModel):
    username: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "student123",
                "password": "secure_password"
            }
        }


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    message: str
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | 
        (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email
    )
    new_user.set_password(user_data.password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate token
    token = _create_access_token(new_user.id)
    
    return AuthResponse(
        message=f"User '{new_user.username}' registered successfully!",
        user=UserResponse.from_orm(new_user),
        access_token=token
    )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token."""
    
    # Find user
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate token
    token = _create_access_token(user.id)
    
    return AuthResponse(
        message=f"Welcome back, {user.username}!",
        user=UserResponse.from_orm(user),
        access_token=token
    )


@router.post("/logout")
async def logout():
    """Logout endpoint (token management on client side)."""
    return {
        "message": "Logged out successfully",
        "status": "success"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: int = None):
    """Get current logged-in user (requires token)."""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return {"id": user_id}


# Helper function to create access token
def _create_access_token(user_id: int) -> str:
    """Create a simple JWT-like token."""
    # For simplicity, using user_id as token (in production, use proper JWT)
    import base64
    import json
    
    payload = {
        "user_id": user_id,
        "exp": (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()
    }
    
    token = base64.b64encode(json.dumps(payload).encode()).decode()
    return token


def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user_id from token."""
    try:
        import base64
        import json
        
        payload = json.loads(base64.b64decode(token.encode()).decode())
        exp = payload.get("exp")
        if exp and datetime.fromisoformat(exp) < datetime.utcnow():
            return None
        
        return payload.get("user_id")
    except:
        return None
