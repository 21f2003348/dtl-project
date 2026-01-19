"""Routes for managing search history."""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models import SearchHistory, User
from routes.auth_routes import get_user_id_from_token

router = APIRouter(prefix="/history", tags=["search history"])


# Pydantic models
class SearchHistoryResponse:
    def __init__(self, search: SearchHistory):
        self.id = search.id
        self.origin = search.origin
        self.destination = search.destination
        self.city = search.city
        self.user_type = search.user_type
        self.group_size = search.group_size
        self.group_type = search.group_type
        self.selected_option = search.selected_option
        self.total_cost = search.total_cost
        self.duration = search.duration
        self.created_at = search.created_at.isoformat() if search.created_at else None
    
    def to_dict(self):
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "city": self.city,
            "user_type": self.user_type,
            "group_size": self.group_size,
            "group_type": self.group_type,
            "selected_option": self.selected_option,
            "total_cost": self.total_cost,
            "duration": self.duration,
            "created_at": self.created_at
        }


def get_user_id_from_header(authorization: str = Header(None)) -> Optional[int]:
    """Extract user_id from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return user_id
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )


@router.get("/list")
async def get_search_history(
    authorization: str = Header(None),
    days: int = Query(30, description="Number of days to retrieve"),
    limit: int = Query(50, description="Max number of results"),
    db: Session = Depends(get_db)
):
    """Get user's search history (last N days)."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get searches from last N days
    since_date = datetime.utcnow() - timedelta(days=days)
    searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == user_id,
        SearchHistory.created_at >= since_date
    ).order_by(SearchHistory.created_at.desc()).limit(limit).all()
    
    history_list = [SearchHistoryResponse(s).to_dict() for s in searches]
    
    return {
        "status": "success",
        "user": user.username,
        "total_searches": len(history_list),
        "searches": history_list,
        "period_days": days
    }


@router.get("/today")
async def get_today_searches(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get searches made today."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    today = datetime.utcnow().date()
    searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == user_id,
        SearchHistory.created_at >= datetime(today.year, today.month, today.day)
    ).order_by(SearchHistory.created_at.desc()).all()
    
    history_list = [SearchHistoryResponse(s).to_dict() for s in searches]
    
    return {
        "status": "success",
        "date": today.isoformat(),
        "total_searches": len(history_list),
        "searches": history_list
    }


@router.delete("/{search_id}")
async def delete_search(
    search_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a specific search from history."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    search = db.query(SearchHistory).filter(
        SearchHistory.id == search_id,
        SearchHistory.user_id == user_id
    ).first()
    
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found or you don't have permission to delete it"
        )
    
    db.delete(search)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Search #{search_id} deleted successfully"
    }


@router.delete("/")
async def clear_all_history(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Clear all search history for the user."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    deleted_count = db.query(SearchHistory).filter(
        SearchHistory.user_id == user_id
    ).delete()
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Deleted {deleted_count} searches from history"
    }


@router.post("/save")
async def save_search(
    search_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Save a search to history."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    try:
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    # Create new search history entry
    new_search = SearchHistory(
        user_id=user_id,
        origin=search_data.get("origin"),
        destination=search_data.get("destination"),
        city=search_data.get("city"),
        user_type=search_data.get("user_type"),
        group_size=search_data.get("group_size", 1),
        group_type=search_data.get("group_type", "solo"),
        query_text=search_data.get("query_text"),
        selected_option=search_data.get("selected_option"),
        total_cost=search_data.get("total_cost"),
        duration=search_data.get("duration")
    )
    
    db.add(new_search)
    db.commit()
    db.refresh(new_search)
    
    return {
        "status": "success",
        "message": "Search saved to history",
        "search_id": new_search.id
    }
