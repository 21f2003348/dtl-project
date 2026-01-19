"""Itinerary management routes for saving and retrieving tourist itineraries."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from database import get_db
from models import Itinerary, User
from routes.auth_routes import get_user_id_from_token

router = APIRouter(prefix="/itinerary", tags=["itinerary"])


class ItinerarySaveRequest(BaseModel):
    """Request to save a new itinerary."""
    title: str
    city: str
    days: int
    num_people: int
    itinerary_data: Dict[str, Any]  # Complete itinerary JSON
    interests: Optional[str] = None
    budget: str = "moderate"


class ItineraryResponse(BaseModel):
    """Response with itinerary details."""
    id: int
    title: str
    city: str
    days: int
    num_people: int
    itinerary_data: Dict[str, Any]
    interests: Optional[str]
    budget: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ItineraryListResponse(BaseModel):
    """Response with list of itineraries."""
    status: str
    user: str
    total_itineraries: int
    itineraries: List[ItineraryResponse]


@router.post("/save", status_code=status.HTTP_201_CREATED)
async def save_itinerary(
    data: ItinerarySaveRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Save a tourist itinerary."""
    
    # Extract user_id from authorization token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to save itinerary"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create itinerary record
    itinerary = Itinerary(
        user_id=user_id,
        title=data.title,
        city=data.city,
        days=data.days,
        num_people=data.num_people,
        itinerary_data=json.dumps(data.itinerary_data),
        interests=data.interests,
        budget=data.budget
    )
    
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)
    
    return {
        "status": "success",
        "message": "Itinerary saved successfully",
        "itinerary_id": itinerary.id,
        "title": itinerary.title,
        "city": itinerary.city
    }


@router.get("/list", response_model=ItineraryListResponse)
async def list_itineraries(
    days: int = 365,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get all itineraries for the authenticated user."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get itineraries within date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    itineraries = db.query(Itinerary).filter(
        Itinerary.user_id == user_id,
        Itinerary.created_at >= cutoff_date
    ).order_by(Itinerary.created_at.desc()).all()
    
    # Parse JSON data for each itinerary
    itinerary_list = []
    for itin in itineraries:
        itinerary_list.append(ItineraryResponse(
            id=itin.id,
            title=itin.title,
            city=itin.city,
            days=itin.days,
            num_people=itin.num_people,
            itinerary_data=json.loads(itin.itinerary_data),
            interests=itin.interests,
            budget=itin.budget,
            created_at=itin.created_at,
            updated_at=itin.updated_at
        ))
    
    return ItineraryListResponse(
        status="success",
        user=user.username,
        total_itineraries=len(itinerary_list),
        itineraries=itinerary_list
    )


@router.get("/{itinerary_id}")
async def get_itinerary(
    itinerary_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific itinerary by ID."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get itinerary and verify ownership
    itinerary = db.query(Itinerary).filter(
        Itinerary.id == itinerary_id,
        Itinerary.user_id == user_id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found"
        )
    
    return {
        "status": "success",
        "itinerary": ItineraryResponse(
            id=itinerary.id,
            title=itinerary.title,
            city=itinerary.city,
            days=itinerary.days,
            num_people=itinerary.num_people,
            itinerary_data=json.loads(itinerary.itinerary_data),
            interests=itinerary.interests,
            budget=itinerary.budget,
            created_at=itinerary.created_at,
            updated_at=itinerary.updated_at
        )
    }


@router.delete("/{itinerary_id}")
async def delete_itinerary(
    itinerary_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a specific itinerary."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get and delete itinerary
    itinerary = db.query(Itinerary).filter(
        Itinerary.id == itinerary_id,
        Itinerary.user_id == user_id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found"
        )
    
    db.delete(itinerary)
    db.commit()
    
    return {
        "status": "success",
        "message": "Itinerary deleted successfully"
    }


@router.delete("/")
async def delete_all_itineraries(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete all itineraries for the authenticated user."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Delete all itineraries for this user
    deleted_count = db.query(Itinerary).filter(
        Itinerary.user_id == user_id
    ).delete()
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Deleted {deleted_count} itineraries"
    }
